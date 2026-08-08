---
policy_id: "POL-SEC-001"
policy_title: "Information Security for Remote Workers"
company: "Northstar Technologies Inc."
version: "1.0"
status: "Active"
effective_date: "2026-09-01"
review_date: "2027-09-01"
owner: "Information Security"
approver: "Chief Information Security Officer"
confidentiality: "Internal"
applies_to: "Employees, contractors, and authorized third parties accessing Northstar information away from a controlled Northstar office"
related_policies: ["POL-RWK-001", "POL-INT-001", "POL-EQP-001", "POL-CON-001", "POL-HRC-001"]
synthetic_corpus: true
---

# Information Security for Remote Workers

> **Educational and synthetic policy corpus.** Northstar Technologies Inc. is a fictional company created for an AI engineering project. All people, records, email addresses, examples, and operational data are synthetic. These documents are not legal advice and do not replace applicable law, benefit plan documents, signed employment agreements, or case-specific guidance from People Operations.


| Metadata | Value |
|---|---|
| Policy ID | **POL-SEC-001** |
| Version | 1.0 |
| Status | Active |
| Effective date | 2026-09-01 |
| Review date | 2027-09-01 |
| Policy owner | Information Security |
| Approver | Chief Information Security Officer |
| Applies to | Employees, contractors, and authorized third parties accessing Northstar information away from a controlled Northstar office |
| Classification | Internal |

## SEC-1. Purpose

This policy establishes minimum information-security controls for remote, hybrid, mobile, and international work. It protects Northstar, employee, customer, and partner information while enabling approved work outside a controlled office.

## SEC-2. Data classification

| Classification | Examples | Remote-work rule |
|---|---|---|
| Public | Published website, approved press release, public job posting | May be handled in ordinary approved business tools |
| Internal | Internal procedures, routine team notes, non-sensitive project plans | Use approved accounts and services; avoid unnecessary local copies |
| Confidential | Employee records, customer information, contracts, source code, non-public financial data | Company-managed device, MFA, encryption, and approved storage required |
| Restricted | Authentication secrets, highly sensitive HR investigations, regulated data, production keys, security incident evidence | Explicit access authorization and enhanced controls; no remote printing or unapproved international access |

When uncertain, employees must treat information as Confidential until the owner or Security confirms otherwise.

## SEC-3. Approved devices and accounts

Confidential or Restricted information may be accessed only from a company-managed device or a specifically approved managed device. Personal computers may not download, synchronize, or store Northstar information. Limited browser access to low-risk Internal information may be allowed only through approved services with MFA and no local download.

Employees must:

- use unique company credentials and MFA;
- never share passwords, tokens, badges, or devices;
- install only approved software;
- allow required patching, encryption, endpoint protection, and device management;
- lock the screen when unattended; and
- use the approved password manager for company secrets.

## SEC-4. Network security

The company VPN must be used when required by the application, Security notice, or data classification. Home Wi-Fi must use WPA2 or stronger security with a non-default administrator password.

Public Wi-Fi should be avoided. When no safer option exists, the employee must use a company hotspot or VPN and must not access Restricted information. Captive portals, shared hotel business centres, public computers, and unknown charging/data cables must not be used for company work.

## SEC-5. Workspace privacy

Employees must position screens and conversations to prevent unauthorized viewing or listening. A headset and private room are required for Confidential discussions when others may overhear. Household members, guests, and service providers must not use company equipment or access company information.

Employees working in temporary lodging must secure devices when leaving the room and avoid leaving badges, notes, or equipment visible. Devices should remain in carry-on possession during travel.

## SEC-6. Storage, sharing, and printing

Company information must be stored in approved company repositories. Employees must not forward company information to personal email, consumer file-sharing services, personal messaging accounts, or removable media.

Printing Confidential information at home requires a documented business need and manager approval. Printing Restricted information outside a controlled office is prohibited unless Security approves a specific exception. Approved paper records must be locked when not in use and destroyed through an approved secure method.

External sharing must use approved channels, least-privilege access, an appropriate expiration date, and verification of the recipient.

## SEC-7. Collaboration, recording, and AI tools

Meetings may be recorded only when participants are notified and the recording is stored in an approved location. Employees must not paste Confidential or Restricted information into public generative-AI tools, public code assistants, public translation tools, or unapproved browser extensions.

Approved enterprise AI services may be used only within their documented data-classification limits. Restricted information requires explicit Security and data-owner approval even when the tool is company licensed.

## SEC-8. International and mobile work

**POL-INT-001** approval is required before working outside the registered province or state. Standard-Risk location status does not remove security requirements.

Security may require a travel device, application restrictions, read-only access, download blocking, temporary credentials, device inspection after return, or complete suspension of access. Restricted information may not be accessed outside the payroll country without explicit written Security approval.

Employees must immediately report unexpected border inspection of a company device, forced credential disclosure, device detention, or any request to install software.

## SEC-9. Physical security and equipment loss

Company equipment must be protected against theft, damage, and unauthorized access. A lost or stolen device, badge, security key, or phone used for MFA must be reported to Security and the manager within one hour of discovery. Employees should not delay reporting while searching for the item.

Security may remotely lock or wipe equipment. Employees must cooperate with replacement, credential reset, incident review, and police or insurer documentation where appropriate.

## SEC-10. Security incidents and accidental disclosure

Report immediately, and no later than one hour after discovery, any suspected phishing success, malware, credential compromise, unauthorized access, accidental external sharing, misdirected email containing Confidential information, or loss of sensitive paper.

Employees should preserve evidence, stop further sharing, disconnect a device from networks when instructed, and avoid independently deleting logs or negotiating with an attacker. Security owns technical containment. People Operations owns employee-related case coordination when the incident involves HR information or conduct.

## SEC-11. Monitoring and privacy

Northstar may log access, device health, network connections, file sharing, and security events for legitimate security, legal, and operational purposes. Monitoring must be proportionate, authorized, and consistent with applicable law. Managers may not deploy informal surveillance or require employees to keep a camera continuously active.

## SEC-12. Exceptions

A security exception must identify the business need, data, duration, compensating controls, owner, and expiration date. The Chief Information Security Officer or delegate must approve exceptions involving Confidential or Restricted information. Convenience alone is not sufficient.

## SEC-13. Enforcement and responsibilities

Employees and contractors are responsible for following controls and reporting concerns promptly. Managers must not pressure staff to bypass security for speed. IT maintains devices and identity services. Security defines controls, investigates incidents, and may suspend access when needed to protect Northstar.

Violations may result in access restriction, corrective action, contract consequences, or legal referral, depending on severity and intent. Good-faith incident reporting is encouraged and will not itself be treated as misconduct.

## SEC-14. Examples

- A Remote employee may review a Confidential customer contract at home on a company laptop using approved storage and required VPN.
- An employee may not upload source code to a public AI assistant, even to debug an urgent problem.
- A traveller in Germany needs the approved international-work decision and must not access Restricted HR case files unless Security explicitly authorizes it.
- A lost phone used for MFA must be reported within one hour, even if the phone has a passcode.

## Related policies and records

- **POL-RWK-001 - Remote and Hybrid Work Policy**
- **POL-INT-001 - International and Out-of-Jurisdiction Work**
- **POL-EQP-001 - Company Equipment and Home Office Equipment**
- **POL-CON-001 - Workplace Conduct and Reporting**
- **POL-HRC-001 - HR Case Management and Escalation**
