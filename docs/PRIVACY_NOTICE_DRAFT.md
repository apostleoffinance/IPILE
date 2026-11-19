# IPÌLẸ̀ privacy notice — publication draft

**Status: Draft requiring controller identity, contact details, retention periods and legal review before publication.**

IPÌLẸ̀ is a household finance service. This notice explains the information the service is designed to process and the controls currently implemented. It must be reviewed against actual hosting, analytics, email and error-reporting vendors before it is published as a binding privacy notice.

## Information processed

Depending on the features a household uses, IPÌLẸ̀ may process:

- Account registration details such as email address and display name.
- Household membership, roles, invitations and preferences.
- Financial records entered or imported by household members, including accounts, balances, income, expenses, budgets, obligations, savings, investments, debts and reports.
- Support requests and correspondence submitted through the service.
- Security and audit information such as session records, request identifiers, timestamps, security events and actions taken in the application.
- Files and statement content submitted for transaction import.

Do not submit bank passwords, card PINs, one-time passcodes or online banking credentials.

## Why information is used

Information is used to:

- Create and secure accounts and household memberships.
- Calculate household financial summaries and forecasts requested by users.
- Import, store, display and export household financial records.
- Provide support and respond to requests.
- Prevent fraud, unauthorized access and cross-household disclosure.
- Maintain service reliability, troubleshoot failures and meet legal obligations.

## Household access and confidentiality

Financial data is scoped to household membership and server-side permissions. Household owners and permitted members receive access according to their roles. Support tickets are currently listed to the user who submitted them. IPÌLẸ̀ operators may require limited access to infrastructure and records for support, security or legal purposes; operator access must be restricted, logged and governed by internal procedures.

## Security

The application uses HTTPS at the hosting edge, password hashing, server-side sessions, CSRF protection, role-based authorization, household-scoped queries, audit events and request identifiers. These controls reduce risk but cannot guarantee absolute security. Production database encryption, backup access controls, error-monitoring scrubbing and operator access controls must be verified for the actual vendors before this notice is finalized.

## Sharing and service providers

IPÌLẸ̀ may rely on hosting, database, email delivery, support, monitoring and payment providers. The final published notice must name or describe the actual providers, processing locations, purposes and applicable transfer safeguards. Do not publish a provider list based on planned integrations.

IPÌLẸ̀ does not need a customer's bank login credentials to support manual transaction entry and statement imports. Any future payment processor will receive only the information required to process a payment.

## Retention and deletion

Users can request a household data export. Household deletion is currently implemented as a soft-delete operation. Soft deletion does not by itself mean all records are immediately erased from database backups, audit records, support records or security logs.

Before publication, IPÌLẸ̀ must approve and publish specific retention periods for:
- Active household financial records.
- Deleted household records and backup expiry.
- Authentication/session and security logs.
- Audit records.
- Imported source files and import metadata.
- Support tickets.
- Error reports.

Deletion requests and applicable legal retention obligations should be handled through a documented process.

## Your choices and rights

Subject to applicable law, users may request access, correction, export, deletion or restriction of personal information and may raise a privacy concern. The final notice must provide a monitored privacy contact and explain how to submit a request.

## Children and dependants

IPÌLẸ̀ supports household records about dependants. Adults responsible for a household should enter only information necessary to manage household finances and should not enter unnecessary sensitive information about children.

## International processing

Hosting and service providers may process information outside the user's country. The final notice must identify actual regions and transfer safeguards after infrastructure and vendor review.

## Changes and contact

The final published notice must identify:
- The legal entity/controller operating IPÌLẸ̀.
- A monitored privacy contact address.
- The effective date and version.
- The applicable complaint/escalation route.

**This draft is not legal advice or a statement of NDPA/NDPC compliance. Obtain qualified Nigerian privacy review and complete the missing operational facts before publication.**
