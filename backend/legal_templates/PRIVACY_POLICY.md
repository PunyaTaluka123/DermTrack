# Privacy Policy - DermTrack

**Last Updated:** [DATE]
**Version:** 1.0
**Contact:** privacy@dermtrack.com

---

## 1. Introduction

This Privacy Policy describes how DermTrack ("we", "us", "our") collects, uses, stores, and protects your personal health information when you use our dermatology consultation recording and transcription service.

We are committed to protecting your privacy and complying with applicable data protection laws, including HIPAA (Health Insurance Portability and Accountability Act) and GDPR (General Data Protection Regulation) where applicable.

---

## 2. Purpose of Data Collection

We collect and process your personal health information for the following purposes:

- **Medical Documentation**: Recording and transcribing doctor-patient consultations for accurate medical record-keeping
- **Clinical Decision Support**: Analyzing consultation data to provide clinical insights and SOAP note generation
- **Quality Improvement**: Improving our transcription accuracy and clinical documentation tools
- **Legal Compliance**: Meeting regulatory requirements for medical record retention
- **Consent Management**: Tracking and maintaining patient consent records

We do NOT use your data for marketing, advertising, or any purpose unrelated to providing healthcare services.

---

## 3. Data We Collect

### 3.1 Clinical Data
- **Audio/Video Recordings**: Doctor-patient consultation recordings
- **Transcripts**: Text transcriptions of consultations
- **Clinical Notes**: SOAP notes and other documentation
- **Patient Information**: Name, medical record number, date of birth (as provided by healthcare provider)

### 3.2 Account Data
- **Doctor/Clinic Information**: Email, name, clinic affiliation
- **Authentication Data**: Password (encrypted), session tokens
- **Usage Data**: Access logs, timestamps, IP addresses

### 3.3 Consent Records
- Consent timestamps and method (verbal, written, digital)
- Consent version and status (active/withdrawn)

---

## 4. Data Storage and Security

### 4.1 Storage Location
- All data is stored in segregated, encrypted storage with separate folders for:
  - Raw recordings (temporary)
  - Processed transcripts (temporary)
  - Metadata
  - Audit logs

### 4.2 Encryption
- **At Rest**: AES-256-GCM encryption for all stored data
- **In Transit**: TLS 1.3 for all network communications
- **Key Management**: Separate encryption keys per clinic, rotated monthly
- **No Hardcoded Keys**: All encryption keys stored in secure environment variables or managed key stores

### 4.3 Access Controls
- **Role-Based Access Control (RBAC)**: Strict permissions based on user role
- **Session Timeout**: Automatic logout after 30 minutes of inactivity
- **Audit Logging**: Every data access is logged with user ID, timestamp, IP address, and action

---

## 5. Data Retention and Deletion

We follow strict retention policies to minimize data storage:

| Data Type | Retention Period | Auto-Deletion |
|-----------|-----------------|---------------|
| Raw audio/video recordings | **24 hours maximum** | Yes, automatic |
| Processed transcripts | **30 days maximum** | Yes, automatic |
| Anonymized training data | **5 years maximum** | Yes, automatic |
| Consent records | **7 years** | No (legal requirement) |
| Audit logs | **7 years** | No (legal requirement) |

### 5.1 Automatic Deletion Process
1. Files are uploaded and assigned a scheduled deletion date
2. System calculates SHA-256 checksum for integrity verification
3. Data is processed and returned to authorized users
4. Automated cron job runs hourly to delete expired files
5. Deletion is logged with timestamp and file hash for compliance

---

## 6. Data Sharing and Third Parties

### 6.1 No Data Resale
**We NEVER sell, rent, or share your personal health information with third parties for marketing purposes.**

### 6.2 Service Providers
We may share data with:
- **Cloud Infrastructure Providers**: For secure data storage (AWS, Google Cloud, etc.)
- **AI/ML Services**: For transcription and clinical note generation (Google Gemini API, OpenAI Whisper)

All service providers:
- Sign Business Associate Agreements (BAAs) as required by HIPAA
- Are contractually obligated to protect your data
- Cannot use your data for their own purposes

### 6.3 Legal Requirements
We may disclose information when required by:
- Court orders or legal process
- Law enforcement requests with proper authorization
- Medical emergencies where disclosure may prevent harm

---

## 7. Your Rights

You have the following rights regarding your personal health information:

### 7.1 Right of Access
- Request copies of your consultation recordings and transcripts
- Access your consent records and audit trail

### 7.2 Right to Rectification
- Request correction of inaccurate or incomplete data

### 7.3 Right to Erasure ("Right to be Forgotten")
- Request deletion of your data before the scheduled retention period
- Some data may be retained for legal compliance (audit logs, consent records)

### 7.4 Right to Withdraw Consent
- Withdraw consent for data processing at any time
- Affects future processing; previously processed data subject to retention policies

### 7.5 Right to Data Portability
- Request your data in a machine-readable format (JSON, CSV)
- Transfer your data to another provider

### 7.6 Right to Object
- Object to processing of your data for specific purposes
- We will evaluate and respond within 30 days

---

## 8. Consent Management

### 8.1 Obtaining Consent
Before recording any consultation, we require explicit patient consent via:
- **Verbal consent**: Recorded at the beginning of the consultation
- **Written consent**: Signed form on file
- **Digital consent**: Electronic consent via patient portal

### 8.2 Consent Information
We store the following consent metadata (separate from clinical data):
- Unique consent ID
- Doctor ID and patient reference
- Consent method and timestamp
- Consent policy version
- Withdrawal status and timestamp (if applicable)
- Notes and additional context

### 8.3 Withdrawing Consent
Patients may withdraw consent by:
- **Email**: privacy@dermtrack.com
- **Phone**: [PHONE NUMBER]
- **In-person**: Through their healthcare provider

Upon withdrawal:
- No new recordings will be made
- Existing data will be deleted according to retention policy (raw data within 24 hours)
- Withdrawal is logged for compliance

---

## 9. Data Breach Notification

In the event of a data breach:

1. **Immediate Investigation**: Within 24 hours of discovery
2. **Affected Party Notification**: Within 72 hours
3. **Regulatory Notification**: As required by HIPAA/GDPR
4. **Remediation**: Immediate steps to prevent further unauthorized access

Notifications will include:
- Nature of the breach
- Types of data affected
- Steps we're taking to address the breach
- Recommended actions for affected individuals
- Contact information for questions

---

## 10. Children's Privacy

DermTrack is designed for use by healthcare providers. We do not knowingly collect data from children under 13 without parental consent. If a consultation involves a minor patient, the healthcare provider is responsible for obtaining appropriate parental/guardian consent.

---

## 11. International Data Transfers

If you are located outside the United States:
- Your data may be transferred to and stored on servers in the United States
- We ensure appropriate safeguards are in place (Standard Contractual Clauses, Privacy Shield framework where applicable)
- You have the same rights regardless of where data is stored

---

## 12. Updates to This Policy

We may update this Privacy Policy to reflect:
- Changes in our practices
- Legal or regulatory requirements
- New features or services

When we make significant changes:
- We will update the "Last Updated" date
- We will notify you via email or in-app notification
- Your continued use of DermTrack constitutes acceptance of the updated policy

---

## 13. Contact Information

### Data Protection Officer (DPO)
**Email**: dpo@dermtrack.com
**Phone**: +1-XXX-XXX-XXXX
**Address**: [PHYSICAL ADDRESS]

### Privacy Questions
**Email**: privacy@dermtrack.com

### Data Subject Requests
To exercise your rights (access, deletion, portability, etc.):
**Email**: privacy@dermtrack.com
**Subject Line**: "Data Subject Request - [Your Name]"

We will respond to all requests within 30 days.

---

## 14. Compliance Certifications

DermTrack is compliant with:
- ✓ HIPAA (Health Insurance Portability and Accountability Act)
- ✓ GDPR (General Data Protection Regulation)
- ✓ HITECH (Health Information Technology for Economic and Clinical Health Act)
- ✓ SOC 2 Type II (pending)

Audit reports available upon request to authorized parties.

---

## 15. Automated Decision-Making

We use AI/ML for:
- Speech-to-text transcription
- SOAP note generation
- Clinical suggestion prompts

**Important**: All AI-generated content is for assistance only. Healthcare providers maintain full responsibility for clinical decisions. No automated decisions are made without human review.

---

## Acceptance

By using DermTrack, you acknowledge that you have read and understood this Privacy Policy and agree to its terms.

For patients: Your healthcare provider has obtained your consent to record and process your consultation data as described in this policy.

---

**DermTrack Privacy Policy v1.0**
**Effective Date**: [DATE]
