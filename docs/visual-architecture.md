# ForayNL2025 Visual Architecture Guide

This document provides a comprehensive visual overview of the ForayNL2025 Django application architecture using Mermaid diagrams. Each diagram illustrates different aspects of the system's design, connections, and workflows.

## 📊 Diagram Index

### System Architecture Diagrams
1. [System Overview](#system-overview) - High-level external connections
2. [Data Flow Pipeline](#data-flow-pipeline) - Processing workflow
3. [Database Relationships](#database-relationships) - Data model connections
4. [Component Architecture](#component-architecture) - Internal system structure

### User Interface Diagrams
5. [Expert Review Workflow](#expert-review-workflow) - User interaction flows
6. [Administrative Workflow](#administrative-workflow) - Admin processes

### Integration Diagrams
7. [External Systems Integration](#external-systems-integration) - Service communication
8. [Container Architecture](#container-architecture) - Docker deployment

## System Overview

```mermaid
graph TB
    subgraph "External Data Sources"
        GD[Google Drive<br/>CSV Files]
        MB[MycoBank Database<br/>Taxonomic References]
        FL[Flickr API<br/>Image Management]
    end
    
    subgraph "Automation Layer"
        FA[FastAPI Server<br/>Webhook Handler]
        PY[Python Scripts<br/>Data Processing]
    end
    
    subgraph "Django Application"
        WEB[Web Interface<br/>Review & Validation]
        DB[PostgreSQL<br/>Data Storage]
        MGMT[Management Commands<br/>Pipeline Control]
    end
    
    subgraph "Users"
        EXP[Expert Mycologists<br/>Taxonomic Reviewers]
        ADM[System Administrators<br/>Data Managers]
    end
    
    GD -->|Push Notifications| FA
    FA -->|Triggers Processing| PY
    PY -->|CSV Import| MGMT
    MGMT -->|Data Pipeline| DB
    MB -->|Taxonomic Lookup| PY
    
    EXP -->|Review & Validate| WEB
    ADM -->|Administration| WEB
    WEB <-->|CRUD Operations| DB
    
    DB -->|Export CSV| EXP
    FL -.->|Future Integration| PY
    
    style FA fill:#e1f5fe
    style WEB fill:#f3e5f5
    style DB fill:#e8f5e8
    style EXP fill:#fff3e0
```

**Key Connections:**
- **External Data Flow**: Google Drive → FastAPI → Django Management Commands → Database
- **User Interactions**: Experts ↔ Web Interface ↔ Database
- **Administrative Control**: System Admins → Web Interface → All System Components
- **Future Integration**: Flickr API (planned for image management)

## Data Flow Pipeline

```mermaid
flowchart LR
    subgraph "Input Sources"
        CSV1[Foray CSV<br/>2023ForayNL_Fungi.csv]
        CSV2[MycoBank CSV<br/>MBList.csv]
    end
    
    subgraph "Data Processing Pipeline"
        IMP[Import Process<br/>load_full_pipeline]
        ALG[Matching Algorithm<br/>full_match_pipeline.py]
        CAT[Categorization<br/>Perfect/Mismatch/Scores]
    end
    
    subgraph "Database Storage"
        FF[ForayFungi2023<br/>Original Data]
        MB[MycoBankList<br/>Reference Data]
        FM[ForayMatch<br/>Match Categories]
        PM[Perfect Matches]
        MM[Mismatch Explanations]
        PMM[Perfect Myco Matches]
        MMS[Mismatch Myco Scores]
    end
    
    subgraph "Web Interface"
        DASH[Dashboard<br/>Match Statistics]
        BROWSE[Match Browser<br/>Category Views]
        DETAIL[Detail View<br/>Individual Records]
        REVIEW[Review Form<br/>Validation Interface]
    end
    
    subgraph "Review Workflow"
        VAL[Expert Validation<br/>Name Correction]
        RM[ReviewedMatch<br/>Validation Results]
        EXP[CSV Export<br/>Final Dataset]
    end
    
    CSV1 --> IMP
    CSV2 --> IMP
    IMP --> FF
    IMP --> MB
    
    FF --> ALG
    MB --> ALG
    ALG --> FM
    
    FM --> PM
    FM --> MM
    FM --> PMM
    FM --> MMS
    
    FM --> DASH
    PM --> BROWSE
    MM --> BROWSE
    PMM --> BROWSE
    MMS --> BROWSE
    
    BROWSE --> DETAIL
    DETAIL --> REVIEW
    REVIEW --> VAL
    VAL --> RM
    RM --> EXP
    
    style IMP fill:#e3f2fd
    style ALG fill:#f3e5f5
    style VAL fill:#e8f5e8
    style EXP fill:#fff3e0
```

**Processing Flow:**
1. **Input**: CSV files with foray and MycoBank data
2. **Import**: Django management command processes files
3. **Matching**: Algorithm compares foray names with MycoBank references  
4. **Categorization**: Results classified as perfect matches, mismatches, or scored similarities
5. **Review**: Web interface provides expert validation workflow
6. **Export**: Final validated dataset exported as CSV

## Database Relationships

```mermaid
erDiagram
    %% Source Tables
    ForayFungi2023 {
        string foray_id PK
        text genus_and_species_org_entry
        text genus_and_species_conf  
        text genus_and_species_foray_name
    }
    
    MycoBankList {
        string mycobank_id PK
        text taxon_name
        text current_name
        text authors
        text year
        text hyperlink
    }
    
    %% Match Processing Results
    ForayMatch {
        int id PK
        string foray_id FK
        string org_entry
        string conf_name
        string foray_name
        string match_category
    }
    
    ForayPerfectMatch {
        int id PK
        string foray_id FK
        string name
    }
    
    ForayMismatchExplanation {
        int id PK
        string foray_id FK
        string org_entry
        string conf_name
        string foray_name
        string explanation
    }
    
    ForayPerfectMycoMatch {
        int id PK
        string foray_id FK
        string matched_name
        string mycobank_id FK
        string mycobank_name
    }
    
    ForayMismatchMycoScores {
        int id PK
        string foray_id FK
        float org_score
        float conf_score
        float foray_score
        string mycobank_id FK
        string mycobank_name
        string mycobank_expl
    }
    
    %% Review Workflow
    ReviewedMatch {
        int id PK
        string foray_id UK
        string org_entry
        string conf_name
        string foray_name
        string validated_name
        string reviewer_name
        string status
        datetime reviewed_at
    }
    
    %% Relationships
    ForayFungi2023 ||--o{ ForayMatch : "foray_id"
    ForayMatch ||--o| ForayPerfectMatch : "foray_id (ALL_MATCH)"
    ForayMatch ||--o| ForayMismatchExplanation : "foray_id (mismatch)"
    ForayMatch ||--o| ForayPerfectMycoMatch : "foray_id (perfect)"
    ForayMatch ||--o| ForayMismatchMycoScores : "foray_id (scores)"
    
    MycoBankList ||--o{ ForayPerfectMycoMatch : "mycobank_id"
    MycoBankList ||--o{ ForayMismatchMycoScores : "mycobank_id"
    
    ForayFungi2023 ||--o| ReviewedMatch : "foray_id"
```

**Key Relationships:**
- **Source Data**: ForayFungi2023 and MycoBankList store original imported data
- **Match Processing**: ForayMatch acts as central hub linking to specialized match result tables
- **Review System**: ReviewedMatch tracks expert validation with one-to-one mapping to ForayFungi2023
- **MycoBank Integration**: Perfect matches and scored matches reference MycoBank records

## Component Architecture

```mermaid
graph TB
    subgraph "Presentation Layer"
        TEMP[Django Templates<br/>HTML/CSS/JS]
        VIEW[Django Views<br/>HTTP Handlers]
        FORM[Django Forms<br/>Validation Logic]
        URL[URL Routing<br/>Endpoint Mapping]
    end
    
    subgraph "Business Logic Layer"
        LOGIC[Business Logic<br/>core/logic/]
        MGMT[Management Commands<br/>Pipeline Control]
        ADMIN[Django Admin<br/>Administrative Interface]
    end
    
    subgraph "Data Access Layer"
        MODEL[Django Models<br/>ORM Mapping]
        MIG[Database Migrations<br/>Schema Management]
        DB[(PostgreSQL<br/>Database)]
    end
    
    subgraph "External Integration"
        FA_INT[FastAPI Integration<br/>Webhook Handler]
        CSV_PROC[CSV Processing<br/>Data Import/Export]
        MYCO_INT[MycoBank Integration<br/>Taxonomic Lookup]
    end
    
    subgraph "Security & Configuration"
        AUTH[Authentication<br/>Django Auth System]
        PERM[Permissions<br/>Access Control]
        CONF[Configuration<br/>Environment Settings]
        SEC[Security Middleware<br/>Headers & Protection]
    end
    
    %% Presentation Layer Connections
    URL --> VIEW
    VIEW --> TEMP
    VIEW --> FORM
    FORM --> VIEW
    
    %% Business Logic Connections
    VIEW --> LOGIC
    LOGIC --> MODEL
    MGMT --> LOGIC
    MGMT --> MODEL
    ADMIN --> MODEL
    
    %% Data Access Connections
    MODEL --> DB
    MIG --> DB
    
    %% External Integration Connections
    FA_INT --> MGMT
    CSV_PROC --> LOGIC
    MYCO_INT --> LOGIC
    
    %% Security Connections
    AUTH --> VIEW
    PERM --> VIEW
    SEC --> VIEW
    CONF --> AUTH
    
    %% Cross-layer connections
    VIEW --> MODEL
    ADMIN --> AUTH
    LOGIC --> CSV_PROC
    
    style TEMP fill:#e3f2fd
    style LOGIC fill:#f3e5f5
    style MODEL fill:#e8f5e8
    style FA_INT fill:#fff3e0
    style AUTH fill:#ffebee
```

**Architecture Layers:**
- **Presentation**: Django templates, views, forms, and URL routing
- **Business Logic**: Core application logic, management commands, admin interface
- **Data Access**: Django ORM, models, database migrations
- **Integration**: External service connectors (FastAPI, CSV processing, MycoBank)
- **Security**: Authentication, permissions, configuration, security middleware

## Expert Review Workflow

```mermaid
graph TD
    START([Expert Accesses System]) --> DASH[Dashboard<br/>View Match Statistics]
    
    DASH --> CHOOSE{Choose Activity}
    
    CHOOSE -->|Browse Matches| BROWSE[Match Browser<br/>Filter by Category]
    CHOOSE -->|View Pending Reviews| PENDING[Pending Reviews<br/>Unvalidated Matches]
    CHOOSE -->|Export Data| EXPORT[CSV Export<br/>Download Results]
    
    BROWSE --> LIST[Match List<br/>Paginated Results]
    LIST --> SELECT{Select Match}
    
    SELECT -->|View Details| DETAIL[Match Detail View<br/>Full Information Display]
    SELECT -->|Quick Review| REVIEW[Review Form<br/>Validation Interface]
    
    DETAIL --> INFO{Review Information}
    INFO -->|Sufficient Info| REVIEW
    INFO -->|Need More Context| EXTERNAL[Check External Sources<br/>MycoBank, Literature]
    
    EXTERNAL --> REVIEW
    
    REVIEW --> VALIDATE[Enter Validation<br/>• Validated Name<br/>• Reviewer Name<br/>• Comments]
    
    VALIDATE --> SUBMIT{Submit Review}
    
    SUBMIT -->|Save & Continue| SUCCESS[Success Message<br/>Return to List]
    SUBMIT -->|Save & Export| EXPORT
    SUBMIT -->|Validation Errors| ERROR[Display Errors<br/>Return to Form]
    
    SUCCESS --> LIST
    ERROR --> VALIDATE
    
    PENDING --> REVIEW
    EXPORT --> DOWNLOAD[Generate CSV<br/>Download File]
    DOWNLOAD --> END([Workflow Complete])
    
    style DASH fill:#e3f2fd
    style REVIEW fill:#f3e5f5
    style VALIDATE fill:#e8f5e8
    style EXPORT fill:#fff3e0
```

**User Journey:**
1. **Entry**: Expert accesses dashboard with match statistics
2. **Navigation**: Choose between browsing matches, reviewing pending items, or exporting data
3. **Selection**: Browse categorized matches and select specific items for review
4. **Analysis**: View detailed match information and consult external sources if needed
5. **Validation**: Enter validated taxonomic name and reviewer information
6. **Completion**: Save review and continue with next match or export results

## External Systems Integration

```mermaid
sequenceDiagram
    participant GD as Google Drive
    participant FA as FastAPI Server
    participant DJ as Django App
    participant DB as Database
    participant WEB as Web Interface
    participant USR as Expert User
    
    Note over GD, USR: Automated Data Processing Pipeline
    
    GD->>FA: Push notification<br/>(new/updated files)
    FA->>FA: Verify notification<br/>headers
    FA->>DJ: Trigger pipeline<br/>(background task)
    DJ->>DJ: Run management command<br/>load_full_pipeline
    DJ->>DB: Import CSV data<br/>(ForayFungi2023, MycoBankList)
    DJ->>DB: Execute matching<br/>algorithm
    DJ->>DB: Store match results<br/>(Categories & Scores)
    
    Note over WEB, USR: Expert Review Workflow
    
    USR->>WEB: Access dashboard
    WEB->>DB: Query match statistics
    DB-->>WEB: Return counts by category
    WEB-->>USR: Display dashboard
    
    USR->>WEB: Browse matches<br/>(select category)
    WEB->>DB: Query filtered matches
    DB-->>WEB: Return match list
    WEB-->>USR: Display match browser
    
    USR->>WEB: View match detail<br/>(select foray_id)
    WEB->>DB: Query specific match<br/>+ MycoBank data
    DB-->>WEB: Return detailed info
    WEB-->>USR: Display detail view
    
    USR->>WEB: Submit review<br/>(validated name)
    WEB->>DB: Store ReviewedMatch
    DB-->>WEB: Confirm saved
    WEB-->>USR: Show success message
    
    USR->>WEB: Export reviewed data
    WEB->>DB: Query reviewed matches
    DB-->>WEB: Return CSV data
    WEB-->>USR: Download CSV file
```

**Integration Points:**
- **Google Drive → FastAPI**: Webhook notifications trigger automated processing
- **FastAPI → Django**: Background task execution for data pipeline
- **Django → Database**: All data operations and storage
- **Web Interface ↔ Users**: Complete review and validation workflow
- **Database → Export**: Final validated dataset generation

## Container Architecture

```mermaid
graph TB
    subgraph "Docker Host System"
        subgraph "Application Stack"
            subgraph "Web Layer"
                NGINX_C[nginx Container<br/>- Reverse Proxy<br/>- SSL Termination<br/>- Static File Serving]
            end
            
            subgraph "Application Layer" 
                DJANGO_C[Django Container<br/>- Gunicorn WSGI Server<br/>- Python Application<br/>- Business Logic]
                WORKER_C[Background Workers<br/>- Data Processing<br/>- Pipeline Tasks<br/>- Async Jobs]
            end
            
            subgraph "Data Layer"
                POSTGRES_C[(PostgreSQL Container<br/>- Primary Database<br/>- ACID Transactions<br/>- Full-text Search)]
                REDIS_C[(Redis Container<br/>- Session Storage<br/>- Caching Layer<br/>- Job Queue)]
            end
            
            subgraph "Integration Layer"
                FASTAPI_C[FastAPI Container<br/>- Webhook Handler<br/>- External API Gateway<br/>- Event Processing]
            end
        end
        
        subgraph "Infrastructure"
            VOLUMES[(Persistent Volumes<br/>- Database Data<br/>- Media Files<br/>- Log Files)]
            NETWORKS[Docker Networks<br/>- Internal Communication<br/>- Service Discovery]
            CONFIGS[Configuration<br/>- Environment Variables<br/>- Secrets Management]
        end
        
        subgraph "Monitoring"
            LOGS[Log Aggregation<br/>- Application Logs<br/>- Access Logs<br/>- Error Tracking]
            HEALTH[Health Checks<br/>- Service Status<br/>- Performance Metrics]
        end
    end
    
    subgraph "External Services"
        GD[Google Drive<br/>Data Source]
        BACKUP[External Backup<br/>Cloud Storage]
        CDN[CDN/CloudFlare<br/>Asset Delivery]
    end
    
    %% Container Connections
    NGINX_C --> DJANGO_C
    DJANGO_C --> POSTGRES_C
    DJANGO_C --> REDIS_C
    DJANGO_C --> WORKER_C
    
    FASTAPI_C --> DJANGO_C
    FASTAPI_C --> REDIS_C
    
    %% Infrastructure Connections
    POSTGRES_C --> VOLUMES
    DJANGO_C --> VOLUMES
    REDIS_C --> VOLUMES
    
    NGINX_C --> NETWORKS
    DJANGO_C --> NETWORKS
    POSTGRES_C --> NETWORKS
    REDIS_C --> NETWORKS
    FASTAPI_C --> NETWORKS
    
    DJANGO_C --> CONFIGS
    FASTAPI_C --> CONFIGS
    
    %% Monitoring Connections
    DJANGO_C --> LOGS
    NGINX_C --> LOGS
    FASTAPI_C --> LOGS
    
    DJANGO_C --> HEALTH
    POSTGRES_C --> HEALTH
    
    %% External Connections
    GD --> FASTAPI_C
    POSTGRES_C --> BACKUP
    NGINX_C --> CDN
    
    style NGINX_C fill:#e3f2fd
    style DJANGO_C fill:#f3e5f5
    style POSTGRES_C fill:#e8f5e8
    style FASTAPI_C fill:#fff3e0
    style VOLUMES fill:#f1f8e9
```

**Container Structure:**
- **Web Layer**: nginx handles SSL, static files, and request routing
- **Application Layer**: Django/Gunicorn serves the web application with background workers
- **Data Layer**: PostgreSQL for persistent data, Redis for caching and sessions
- **Integration Layer**: FastAPI handles external webhooks and API integrations
- **Infrastructure**: Persistent volumes, internal networks, and configuration management
- **Monitoring**: Log aggregation and health checking across all services

## 📋 Diagram Summary

### Key Architectural Insights

1. **Modular Design**: Clear separation between data processing, web interface, and external integrations
2. **Scalable Architecture**: Container-based deployment supports horizontal scaling
3. **Robust Data Flow**: Multi-stage processing from raw CSV to validated taxonomic data
4. **User-Centric Workflow**: Expert review interface designed for efficient validation
5. **External Integration**: Webhook-driven automation with Google Drive and MycoBank
6. **Security Considerations**: Multi-layered security from nginx to database access

### Connection Patterns

- **Synchronous Flows**: Web requests, database queries, form submissions
- **Asynchronous Flows**: Webhook processing, background jobs, data pipeline
- **Data Relationships**: Foreign key relationships maintain data integrity
- **Service Communication**: REST APIs, internal network calls, event-driven triggers

### Deployment Considerations

- **Container Orchestration**: Docker Compose for local development, Kubernetes for production
- **Data Persistence**: Volume mounts for database, media files, and logs
- **Network Security**: Internal networks isolate services, external access only through nginx
- **Configuration Management**: Environment variables and secrets for sensitive data
- **Monitoring & Logging**: Centralized logging with health checks for all services

---

This visual guide provides a comprehensive overview of the ForayNL2025 application architecture, illustrating the connections between internal components and external resources that enable taxonomic data validation and expert review workflows.