import { DurableObject, WorkflowEntrypoint } from "cloudflare:workers";

interface Env {
  STATEMENT_QUEUE: Queue<StatementQueueMessage>;
  STATEMENT_WORKFLOW: Workflow<StatementWorkflowParams>;
  STATEMENT_CONTAINER: DurableObjectNamespace<StatementContainer>;
  DATABASE_URL: string;
  INTERNAL_API_SECRET: string;
}

interface StatementQueueMessage {
  task_id: string;
  schema_version: 1;
}

interface StatementWorkflowParams {
  task_id: string;
}

export class StatementContainer extends DurableObject<Env> {
  private ready?: Promise<void>;

  async fetch(request: Request): Promise<Response> {
    await this.ensureStarted();
    const incoming = new URL(request.url);
    incoming.protocol = "http:";
    incoming.hostname = "container";
    incoming.port = "10000";
    const forwarded = new Request(incoming, request);
    forwarded.headers.delete("host");
    forwarded.headers.set("X-Statement-Worker-Secret", this.env.INTERNAL_API_SECRET);
    return this.ctx.container!.getTcpPort(10000).fetch(forwarded);
  }

  private async ensureStarted(): Promise<void> {
    this.ready ??= this.startAndWait().finally(() => {
      this.ready = undefined;
    });
    await this.ready;
  }

  private async startAndWait(): Promise<void> {
    const container = this.ctx.container!;
    if (!container.running) {
      container.start({
        image: container.images.base,
        instance: "standard-1",
        env: {
          ENVIRONMENT: "production",
          DATABASE_URL: this.env.DATABASE_URL,
          INTERNAL_STATEMENT_WORKER_SECRET: this.env.INTERNAL_API_SECRET,
          SEED_ON_START: "false"
        }
      });
    }
    await container.setInactivityTimeout(120_000);
    const port = container.getTcpPort(10000);
    for (let attempt = 0; attempt < 90; attempt++) {
      try {
        const response = await port.fetch("http://container/api/v1/health/live", {
          signal: AbortSignal.timeout(1500)
        });
        await response.body?.cancel();
        if (response.ok) return;
      } catch {
        // Container is still booting; retry readiness only.
      }
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
    throw new Error("Statement extraction container did not become ready.");
  }
}

export class StatementWorkflow extends WorkflowEntrypoint<Env, StatementWorkflowParams> {
  async run(event: { payload: StatementWorkflowParams }, step: any): Promise<void> {
    const taskId = event.payload.task_id;
    await step.do(
      "process-statement",
      {
        retries: { limit: 3, delay: "10 seconds", backoff: "exponential" },
        timeout: "15 minutes"
      },
      async () => {
        const id = this.env.STATEMENT_CONTAINER.idFromName(taskId);
        const container = this.env.STATEMENT_CONTAINER.get(id);
        const response = await container.fetch(
          new Request(`https://container/api/v1/imports/internal/statement-tasks/${encodeURIComponent(taskId)}/process`, {
            method: "POST",
            headers: { "X-Statement-Worker-Secret": this.env.INTERNAL_API_SECRET }
          })
        );
        if (!response.ok) {
          throw new Error(`Statement task processing failed with HTTP ${response.status}: ${(await response.text()).slice(0, 300)}`);
        }
        return await response.json();
      }
    );
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname === "/health") {
      return Response.json({ service: "ipile-statement-jobs", status: "ok" });
    }
    if (url.pathname !== "/internal/dispatch" || request.method !== "POST") {
      return new Response("Not found", { status: 404 });
    }
    const supplied = request.headers.get("Authorization") ?? "";
    if (!env.INTERNAL_API_SECRET || supplied !== `Bearer ${env.INTERNAL_API_SECRET}`) {
      return new Response("Unauthorized", { status: 401 });
    }
    const body = await request.json() as StatementQueueMessage;
    if (body.schema_version !== 1 || !/^[0-9a-f-]{36}$/i.test(body.task_id)) {
      return new Response("Invalid task message", { status: 400 });
    }
    await env.STATEMENT_QUEUE.send(body);
    return Response.json({ accepted: true, task_id: body.task_id }, { status: 202 });
  },
  async queue(batch: MessageBatch<StatementQueueMessage>, env: Env): Promise<void> {
    for (const message of batch.messages) {
      try {
        const workflowId = `statement-${message.body.task_id}`;
        await env.STATEMENT_WORKFLOW.create({
          id: workflowId,
          params: { task_id: message.body.task_id }
        });
        message.ack();
      } catch (error) {
        console.error("Could not start statement workflow", {
          task_id: message.body.task_id,
          error: String(error)
        });
        message.retry();
      }
    }
  }
};
