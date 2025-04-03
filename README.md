Digital Forensics Framework
A comprehensive platform for digital evidence collection, analysis, and authentication with advanced AI-based media verification capabilities.

Overview
The Digital Forensics Framework provides investigators with an integrated environment for handling digital evidence while maintaining strict chain of custody standards. The system combines file analysis, memory examination, email security validation, and AI-powered media authentication to support modern forensic investigations.

Key Features
Evidence Collection: Secure gathering of digital evidence with cryptographic hash verification
Memory Analysis: Real-time memory capture and process monitoring with timeline visualization
Email Security Validation: Comprehensive SPF, DKIM, and DMARC verification for email evidence
Dual-tier AI Authentication:
CNN-based image manipulation detection
Vision Transformer (ViT) architecture for deepfake detection
Chain of Custody: Cryptographically verified custody tracking with full audit trails
Web Dashboard: Intuitive interface with responsive design and evidence visualization


System Architecture
The framework is built on a modular architecture with four specialized databases:

evidence.db: Stores file evidence and analysis results
emails.db: Manages email evidence and security validation data
custody.db: Maintains chain of custody records
users.db: Handles authentication and access control
Technologies
Backend: Python 3.8+, Flask
Databases: SQLite 3.x
AI Components: TensorFlow 2.8+, OpenCV
Memory Analysis: psutil, custom process monitoring
Frontend: HTML5, JavaScript, CSS



