# Data Processing Agreement (DPA)

**Effective Date:** [DATE]
**Version:** 1.0

---

## Parties

This Data Processing Agreement ("DPA") is entered into between:

**DATA CONTROLLER** ("Controller" or "Clinic"):
- Legal Name: [CLINIC/HOSPITAL NAME]
- Address: [CLINIC ADDRESS]
- Contact: [CLINIC CONTACT EMAIL]
- Represented by: [CLINIC REPRESENTATIVE NAME]

AND

**DATA PROCESSOR** ("Processor" or "DermTrack"):
- Legal Name: DermTrack, Inc. [OR APPLICABLE LEGAL ENTITY]
- Address: [DERMTRACK ADDRESS]
- Contact: legal@dermtrack.com
- DPO Contact: dpo@dermtrack.com

---

## 1. Definitions

**1.1** "Personal Data" means any information relating to an identified or identifiable natural person, including Protected Health Information (PHI) as defined under HIPAA.

**1.2** "Processing" means any operation performed on Personal Data, including collection, recording, storage, retrieval, use, disclosure, or destruction.

**1.3** "Sub-processor" means any third party engaged by DermTrack to process Personal Data on behalf of the Controller.

**1.4** "Data Subject" means the individual patient whose Personal Data is processed.

**1.5** "Security Incident" means any unauthorized access, use, disclosure, modification, or destruction of Personal Data.

---

## 2. Roles and Responsibilities

### 2.1 Controller Responsibilities
The Controller (Clinic) is responsible for:
- ✓ Obtaining valid patient consent before recording consultations
- ✓ Ensuring lawful basis for data processing
- ✓ Determining purposes and means of processing
- ✓ Responding to patient requests (access, deletion, etc.)
- ✓ Notifying DermTrack of any consent withdrawal

### 2.2 Processor Responsibilities
The Processor (DermTrack) is responsible for:
- ✓ Processing Personal Data only on documented instructions from Controller
- ✓ Implementing appropriate technical and organizational security measures
- ✓ Ensuring confidentiality of all personnel with access to Personal Data
- ✓ Assisting Controller with data subject requests
- ✓ Deleting or returning Personal Data upon termination of services
- ✓ Maintaining records of processing activities

---

## 3. Data Processing Terms

### 3.1 Scope of Processing
DermTrack is authorized to process the following types of Personal Data:

**Categories of Data Subjects:**
- Patients receiving dermatology consultations

**Categories of Personal Data:**
- Audio/video recordings of consultations
- Text transcripts of consultations
- Patient name, medical record number, date of birth
- Clinical notes and SOAP documentation
- Consent records

**Purpose of Processing:**
- Medical transcription and documentation
- Clinical decision support (SOAP note generation)
- Quality improvement of transcription services
- Legal compliance and audit trail maintenance

**Nature of Processing:**
- Collection, recording, storage, transcription, analysis, deletion

**Duration of Processing:**
- Term of this Agreement plus retention period as defined in Section 5

### 3.2 Processing Instructions
DermTrack shall:
- Process Personal Data only in accordance with documented instructions from Controller
- Not process Personal Data for any purpose other than those specified in Section 3.1
- Immediately inform Controller if any instruction violates applicable data protection law

---

## 4. Data Protection and Security

### 4.1 Security Measures
DermTrack implements the following security measures:

**Encryption:**
- AES-256-GCM encryption for data at rest
- TLS 1.3 for data in transit
- Separate encryption keys per clinic, rotated monthly
- No hardcoded encryption keys

**Access Control:**
- Role-based access control (RBAC) with four levels: Doctor, Admin, Developer, Auditor
- Developers have NO access to raw recordings or identifiable patient data
- Multi-factor authentication for administrative access
- Automatic session timeout after 30 minutes of inactivity

**Audit Logging:**
- Comprehensive logging of all data access
- Logs include: user ID, action, timestamp, resource accessed, IP address
- Audit logs retained for 7 years
- Regular review of access logs for suspicious activity

**Data Segregation:**
- Physical/logical separation of data storage:
  - raw_data (temporary storage)
  - processed_data (temporary storage)
  - metadata (permanent until deleted)
  - audit_logs (7-year retention)

**Integrity Verification:**
- SHA-256 checksums calculated before and after processing
- Hash verification before file deletion
- Versioned anonymization scripts for reproducibility

### 4.2 Personnel Security
- All personnel with access to Personal Data sign confidentiality agreements
- Regular security awareness training
- Background checks for personnel with data access (where legally permitted)
- Principle of least privilege: access granted only as needed for job function

### 4.3 Physical Security
- Data centers with 24/7 physical security
- Biometric access controls
- Video surveillance
- Environmental controls (fire suppression, climate control)

### 4.4 Vulnerability Management
- Regular security assessments and penetration testing
- Patch management program for timely security updates
- Vulnerability scanning and remediation
- Incident response plan tested annually

---

## 5. Data Retention and Deletion

### 5.1 Retention Schedule

DermTrack implements the following automatic deletion schedule:

| Data Type | Retention Period | Deletion Method |
|-----------|------------------|-----------------|
| Raw audio/video | 24 hours maximum | Automated, verified deletion |
| Processed transcripts | 30 days maximum | Automated, verified deletion |
| Anonymized training data | 5 years maximum | Automated, verified deletion |
| Consent records | 7 years | Manual deletion upon request |
| Audit logs | 7 years | Manual deletion upon request |

### 5.2 Deletion Process
Upon expiry of the retention period:
1. Automated cron job identifies files scheduled for deletion
2. System verifies file integrity via SHA-256 checksum
3. File is securely deleted (overwrite + unlink)
4. Deletion is logged with timestamp and original file hash
5. Deletion confirmation available for audit purposes

### 5.3 Deletion Upon Request
Controller may request deletion of specific data before scheduled retention period by:
- **Email**: deletions@dermtrack.com
- **Subject**: "Data Deletion Request - [Clinic Name]"
- **Include**: Patient reference, consent ID, or consultation ID

DermTrack will complete deletion within:
- Raw recordings: 24 hours
- Processed data: 7 days
- Audit logs: No deletion (legal requirement)

### 5.4 Termination of Agreement
Upon termination of this Agreement, DermTrack will:
1. Cease all processing of Personal Data within 30 days
2. Delete or return all Personal Data to Controller (Controller's choice)
3. Delete all existing copies unless required to retain by law
4. Provide certification of deletion upon request

---

## 6. Sub-processors and Third Parties

### 6.1 Authorized Sub-processors
DermTrack may engage the following categories of sub-processors:

**Cloud Infrastructure:**
- Purpose: Data storage and computing
- Examples: AWS, Google Cloud Platform, Microsoft Azure
- Safeguards: BAA signed, encryption at rest, access controls

**AI/ML Services:**
- Purpose: Transcription and clinical note generation
- Examples: Google Gemini API, OpenAI Whisper
- Safeguards: BAA signed, data not retained by provider, no use for training

**Monitoring and Security:**
- Purpose: Security monitoring, intrusion detection
- Examples: Datadog, CloudWatch, Sentry
- Safeguards: Anonymized/aggregated data only, BAA where applicable

### 6.2 Sub-processor Obligations
All sub-processors must:
- Sign Data Processing Agreements with equivalent protections
- Implement appropriate security measures
- Comply with HIPAA, GDPR, and applicable regulations
- Submit to audits upon request

### 6.3 New Sub-processors
DermTrack will:
- Notify Controller at least 30 days before engaging a new sub-processor
- Provide Controller opportunity to object
- Not engage sub-processor if Controller objects on reasonable grounds

### 6.4 No Data Resale or Third-Party Sharing
DermTrack commits to:
- **NEVER** sell, rent, or license Personal Data to third parties
- **NEVER** share Personal Data for marketing purposes
- **NEVER** use Personal Data for purposes unrelated to providing the Service
- **NEVER** allow sub-processors to use Personal Data for their own purposes

---

## 7. Data Subject Rights

### 7.1 Assistance with Requests
DermTrack will assist Controller in responding to Data Subject requests for:
- Access to Personal Data
- Rectification of inaccurate data
- Erasure ("right to be forgotten")
- Restriction of processing
- Data portability
- Objection to processing

### 7.2 Response Timeline
- Acknowledge request within 48 hours
- Provide requested data or assistance within 15 days
- If unable to fulfill within 15 days, provide explanation and estimated completion date

### 7.3 Request Procedure
Data Subjects should submit requests to Controller (Clinic). If received directly by DermTrack:
1. DermTrack will forward request to Controller within 24 hours
2. DermTrack will assist Controller in fulfilling request
3. Final response will come from Controller

---

## 8. Security Incidents and Breach Notification

### 8.1 Security Incident Response
Upon discovering a Security Incident, DermTrack will:
1. **Immediate containment** (within 1 hour of discovery)
2. **Notify Controller** within 24 hours of discovery
3. **Investigate root cause** and document findings
4. **Remediate vulnerability** to prevent recurrence
5. **Provide written report** within 72 hours

### 8.2 Notification Content
Security Incident notifications will include:
- Description of the incident
- Categories and approximate number of Data Subjects affected
- Categories and approximate number of Personal Data records affected
- Likely consequences of the incident
- Measures taken or proposed to address the incident
- Contact point for further information

### 8.3 Regulatory Notification
- Controller is responsible for notifying regulatory authorities (e.g., OCR for HIPAA, supervisory authority for GDPR)
- DermTrack will provide reasonable assistance and information for such notifications
- DermTrack will cooperate with any regulatory investigation

### 8.4 No Public Disclosure
DermTrack will not publicly disclose any Security Incident without prior written consent from Controller, except as required by law.

---

## 9. Audits and Compliance

### 9.1 Right to Audit
Controller has the right to:
- Audit DermTrack's compliance with this DPA
- Appoint independent third-party auditors
- Receive copies of relevant compliance certifications (SOC 2, HITRUST, ISO 27001)

### 9.2 Audit Frequency and Notice
- Audits may be conducted once per year
- Controller must provide 30 days advance written notice
- Audits will be conducted during normal business hours
- Controller will minimize disruption to DermTrack's operations

### 9.3 Audit Reports
DermTrack will provide:
- Annual SOC 2 Type II reports (when available)
- HIPAA compliance documentation
- Penetration test summaries (with sensitive details redacted)
- Security policy documentation

### 9.4 Remediation
If audit reveals non-compliance:
- DermTrack will provide remediation plan within 15 days
- Critical issues remediated within 30 days
- Non-critical issues remediated within 90 days
- Controller may terminate Agreement if critical issues not remediated

---

## 10. Limitation of Liability

### 10.1 Processor Liability
DermTrack's liability is limited to:
- **Direct damages** caused by DermTrack's negligence or willful misconduct
- **Scope**: Processing activities performed by DermTrack or its sub-processors
- **Exclusions**: Liability does NOT extend to:
  - Controller's failure to obtain valid patient consent
  - Controller's unlawful processing instructions
  - Security incidents caused by Controller's negligence
  - Unauthorized access via compromised Controller credentials

### 10.2 Liability Cap
Total liability under this DPA shall not exceed:
- **Greater of**: (a) $1,000,000 USD OR (b) 12 months of Service fees paid by Controller
- **Exception**: No cap on liability for gross negligence, willful misconduct, or fraud

### 10.3 Indemnification
DermTrack will indemnify Controller against claims arising from:
- DermTrack's breach of this DPA
- DermTrack's violation of applicable data protection laws
- Negligent acts or omissions by DermTrack or its sub-processors

Controller will indemnify DermTrack against claims arising from:
- Controller's failure to obtain valid patient consent
- Controller's provision of unlawful processing instructions
- Controller's breach of applicable healthcare regulations

---

## 11. Data Transfers

### 11.1 International Transfers
If Personal Data is transferred outside the European Economic Area (EEA):
- DermTrack will implement Standard Contractual Clauses (SCCs) approved by European Commission
- Supplementary measures will be implemented to ensure GDPR-level protection
- Controller will be notified of the countries where data is stored

### 11.2 US-Based Processing
For data processed in the United States:
- DermTrack complies with HIPAA and HITECH requirements
- Data stored in HIPAA-compliant data centers
- Business Associate Agreement (BAA) executed
- Adequate safeguards in place for international data transfers

---

## 12. Term and Termination

### 12.1 Term
This DPA is effective as of the Effective Date and continues for the duration of the Service Agreement between the parties.

### 12.2 Termination
This DPA may be terminated:
- Upon termination of the Service Agreement
- By either party with 60 days written notice
- By Controller immediately if DermTrack materially breaches this DPA
- By either party if required by regulatory authority

### 12.3 Effect of Termination
Upon termination:
1. DermTrack ceases all processing within 30 days
2. DermTrack deletes or returns all Personal Data (per Controller's instruction)
3. DermTrack deletes all copies and backups (except as required by law)
4. DermTrack provides written certification of deletion
5. Audit logs and consent records retained per legal requirements (7 years)

---

## 13. Governing Law and Disputes

### 13.1 Governing Law
This DPA shall be governed by:
- **US Clients**: Laws of [STATE], United States, and applicable federal law (HIPAA)
- **EU Clients**: Laws of [EU MEMBER STATE] and GDPR

### 13.2 Dispute Resolution
Disputes shall be resolved through:
1. **Good faith negotiation** (30 days)
2. **Mediation** (if negotiation fails)
3. **Arbitration** (binding, [ARBITRATION RULES])
4. **Litigation** (only if arbitration fails or is unavailable)

### 13.3 Regulatory Cooperation
Both parties agree to cooperate fully with any investigation by regulatory authorities (OCR, ICO, CNIL, etc.).

---

## 14. Amendments

### 14.1 Amendment Process
This DPA may be amended:
- By mutual written agreement of both parties
- By DermTrack to reflect changes in law (with 60 days notice)
- Controller may object to amendments within 30 days; if objection not resolved, Controller may terminate Agreement

### 14.2 Precedence
In case of conflict between this DPA and the Service Agreement:
- This DPA takes precedence on data protection matters
- Service Agreement takes precedence on other matters

---

## 15. Signatures

**DATA CONTROLLER (Clinic):**

Signature: _______________________________
Name: [PRINT NAME]
Title: [TITLE]
Date: [DATE]

---

**DATA PROCESSOR (DermTrack):**

Signature: _______________________________
Name: [PRINT NAME]
Title: [TITLE]
Date: [DATE]

---

## Appendix A: Technical and Organizational Measures

### Encryption
- Algorithm: AES-256-GCM
- Key length: 256 bits
- Key rotation: Monthly per clinic
- Key storage: AWS KMS, HashiCorp Vault, or secure environment variables
- Transport: TLS 1.3 minimum

### Access Control
- Authentication: Multi-factor authentication (MFA) for admin roles
- Authorization: Role-based access control (RBAC)
  - Doctor: Full access to own patient data
  - Admin: User management, audit logs
  - Developer: Anonymized data only
  - Auditor: Read-only audit logs
- Session management: 30-minute idle timeout

### Audit Logging
- Events logged: All access, modifications, deletions, exports
- Log retention: 7 years
- Log contents: User ID, timestamp (UTC), IP address, action, resource, success/failure
- Log protection: Append-only, encrypted, tamper-evident

### Data Minimization
- Collect only data necessary for service provision
- Anonymize data for analytics and training
- Delete raw recordings within 24 hours
- Delete processed transcripts within 30 days

### Backup and Recovery
- Backup frequency: Daily incremental, weekly full
- Backup encryption: AES-256
- Backup retention: 30 days
- Recovery time objective (RTO): 4 hours
- Recovery point objective (RPO): 24 hours

### Incident Response
- 24/7 security monitoring
- Automated threat detection
- Incident response team on-call
- Incident response plan tested annually
- Post-incident review and lessons learned

---

**END OF DATA PROCESSING AGREEMENT**

**DermTrack DPA v1.0**
**Effective Date**: [DATE]
