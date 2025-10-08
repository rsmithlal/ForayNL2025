# Architecture Overview

## System Design

The ForayNL2025 Django application is designed as a taxonomic validation system that processes fungal collection data and facilitates expert review of species identifications.

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

## Application Structure

```
FORAY_DJANGO/
├── config/                 # Django configuration
│   ├── settings.py        # Application settings
│   ├── urls.py           # Main URL routing
│   └── wsgi.py           # WSGI application entry
├── core/                   # Main application logic
│   ├── models.py          # Data models
│   ├── views.py          # HTTP request handlers
│   ├── forms.py          # Form definitions
│   ├── admin.py          # Django admin configuration
│   ├── urls.py           # Application URL routing
│   ├── templates/        # HTML templates
│   ├── logic/            # Business logic
│   ├── management/       # Django management commands
│   └── migrations/       # Database migrations
└── data/                  # Static data files
    ├── 2023ForayNL_Fungi.csv
    └── MBList.csv
```

## Data Flow Architecture

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

## Core Components

### 1. Data Import Layer
- **Purpose**: Process CSV files containing foray collection data
- **Components**: Management commands, CSV parsing logic
- **Data Sources**: ForayNL field collection data, MycoBank taxonomic records

### 2. Matching Engine
- **Purpose**: Compare foray specimens with MycoBank taxonomic database
- **Algorithm**: String similarity matching with configurable thresholds
- **Output**: Categorized matches (perfect, mismatch, all_match)

### 3. Review Interface
- **Purpose**: Provide web UI for expert taxonomic validation
- **Features**: Dashboard, detail views, validation forms, export functions
- **Users**: Mycologists, taxonomic experts, research coordinators

### 4. Data Management
- **Purpose**: Store and organize matching results and validations
- **Storage**: PostgreSQL database with proper relationships
- **Versioning**: Track reviewer information and validation history

## Integration Points

### External Systems Integration

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

### External System Details
- **FastAPI Server**: Handles Google Drive push notifications and triggers automated processing
- **Google Drive**: Source for new data files with webhook integration
- **Flickr API**: Image management (separate automation system, future integration)
- **MycoBank Database**: Taxonomic reference data for species validation

## Technology Stack

### Backend
- **Django 4.0+**: Web framework
- **Python 3.8+**: Programming language
- **PostgreSQL**: Production database (SQLite for development)
- **Gunicorn**: WSGI server for production

### Frontend
- **Django Templates**: Server-side rendering
- **Bootstrap CSS**: UI framework
- **JavaScript**: Client-side interactions
- **CSV Export**: Data download functionality

### Infrastructure
- **Docker**: Containerization (recommended)
- **nginx**: Reverse proxy and static file serving
- **SSL/TLS**: HTTPS encryption
- **Environment Variables**: Configuration management

## Security Architecture

### Authentication & Authorization
- **Django Admin**: Built-in administrative interface
- **Session Management**: Django's session framework
- **CSRF Protection**: Cross-site request forgery prevention
- **XSS Protection**: Cross-site scripting prevention

### Data Protection
- **Input Validation**: Form-based validation and sanitization
- **SQL Injection Prevention**: Django ORM protection
- **File Upload Security**: Type and size restrictions
- **Environment Configuration**: Secure settings management

### Network Security
- **HTTPS Enforcement**: SSL/TLS for all traffic
- **Security Headers**: HSTS, XSS protection, content type sniffing prevention
- **Host Validation**: ALLOWED_HOSTS configuration
- **Database Encryption**: Connection security

## Performance Considerations

### Database Optimization
- **Indexes**: Strategic indexing on frequently queried fields
- **Query Optimization**: Efficient ORM usage
- **Connection Pooling**: Database connection management
- **Bulk Operations**: Efficient data processing for large datasets

### Caching Strategy
- **Django Cache Framework**: Page and query caching
- **Static Files**: CDN or optimized serving
- **Database Caching**: Query result caching
- **Session Optimization**: Efficient session storage

### Scalability Planning
- **Horizontal Scaling**: Load balancer support
- **Database Scaling**: Read replicas and connection pooling
- **Background Processing**: Celery for heavy operations (if needed)
- **File Storage**: Separate static/media file serving

## Error Handling & Monitoring

### Logging Strategy
```python
LOGGING = {
    'version': 1,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/django.log',
        },
        'security': {
            'level': 'WARNING',
            'class': 'logging.FileHandler', 
            'filename': 'logs/security.log',
        },
    },
    'loggers': {
        'django': {'handlers': ['file'], 'level': 'INFO'},
        'django.security': {'handlers': ['security'], 'level': 'WARNING'},
        'core': {'handlers': ['file'], 'level': 'DEBUG'},
    },
}
```

### Error Recovery
- **Database Transactions**: ACID compliance for data integrity
- **Backup Strategy**: Regular automated backups
- **Health Checks**: Application monitoring endpoints
- **Graceful Degradation**: Fallback behaviors for failures

## Deployment Architecture

### Development Environment
```
Local Machine → SQLite → Django Development Server → localhost:8000
```

### Production Environment
```
Internet → Load Balancer → nginx → Gunicorn → Django App → PostgreSQL
                    ↓
                Static Files → CDN/nginx
```

### Container Architecture (Recommended)
```
Docker Container:
├── nginx (reverse proxy)
├── gunicorn (WSGI server)
├── Django application
└── PostgreSQL (or external DB)
```

## API Design (Future Considerations)

### RESTful Endpoints (Not Yet Implemented)
- `GET /api/matches/` - List all matches
- `GET /api/matches/{id}/` - Get specific match
- `POST /api/review/` - Submit review
- `GET /api/export/` - Export validated data

### Authentication (Future)
- Token-based authentication
- API key management
- Rate limiting
- CORS configuration

## User Interface Workflows

### Expert Review Workflow

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

### Administrative Workflow

```mermaid
graph TD
    ADMIN([Administrator Login]) --> ADMIN_DASH[Admin Dashboard<br/>System Management]
    
    ADMIN_DASH --> ADMIN_CHOOSE{Administrative Task}
    
    ADMIN_CHOOSE -->|Data Management| DATA_MGMT[Data Management<br/>• Import new CSV<br/>• Run pipeline<br/>• Clear old data]
    ADMIN_CHOOSE -->|User Management| USER_MGMT[User Management<br/>• Add reviewers<br/>• Manage permissions<br/>• View activity logs]
    ADMIN_CHOOSE -->|System Monitoring| SYS_MON[System Monitoring<br/>• Performance metrics<br/>• Error logs<br/>• Database status]
    
    DATA_MGMT --> PIPELINE{Pipeline Action}
    PIPELINE -->|Import Data| IMPORT[Upload CSV Files<br/>Run Import Process]
    PIPELINE -->|Process Matches| PROCESS[Execute Matching<br/>Generate Results]
    PIPELINE -->|Clear Database| CLEAR[Remove Old Data<br/>Prepare for New Import]
    
    USER_MGMT --> USER_ACTION{User Action}
    USER_ACTION -->|Add User| ADD_USER[Create New Reviewer<br/>Set Permissions]
    USER_ACTION -->|View Activity| VIEW_ACTIVITY[Review Logs<br/>Track Progress]
    
    SYS_MON --> MONITOR{Monitoring Type}
    MONITOR -->|Performance| PERF[Check Response Times<br/>Database Performance]
    MONITOR -->|Errors| ERROR_LOG[Review Error Logs<br/>System Issues]
    MONITOR -->|Usage| USAGE[User Activity<br/>System Utilization]
    
    IMPORT --> VERIFY[Verify Import<br/>Check Data Quality]
    PROCESS --> CHECK[Check Results<br/>Validate Output]
    
    VERIFY --> COMPLETE[Process Complete<br/>Return to Dashboard]
    CHECK --> COMPLETE
    ADD_USER --> COMPLETE
    PERF --> COMPLETE
    ERROR_LOG --> COMPLETE
    
    COMPLETE --> ADMIN_DASH
    
    style ADMIN_DASH fill:#e3f2fd
    style DATA_MGMT fill:#f3e5f5
    style SYS_MON fill:#e8f5e8
    style USER_MGMT fill:#fff3e0
```

## Component Architecture

### Django Application Components

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

## Configuration Management

### Environment-Based Configuration
```python
# Development
DEBUG = True
DATABASE_URL = 'sqlite:///db.sqlite3'
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Production  
DEBUG = False
DATABASE_URL = 'postgresql://user:pass@db:5432/foray_db'
ALLOWED_HOSTS = ['foray.example.com']
```

### Settings Organization
```python
# settings/
├── base.py      # Common settings
├── development.py  # Development overrides
├── production.py   # Production overrides
└── testing.py      # Test environment
```

## Testing Strategy

### Test Categories
- **Unit Tests**: Model and form validation
- **Integration Tests**: View and URL routing
- **Functional Tests**: Complete user workflows
- **Security Tests**: Authentication and authorization

### Test Structure
```
tests/
├── test_models.py      # Data model tests
├── test_views.py       # HTTP view tests
├── test_forms.py       # Form validation tests
├── test_security.py    # Security configuration tests
└── test_pipeline.py    # Data processing tests
```

## Future Enhancements

### Short-term Improvements
- Comprehensive test suite implementation
- API endpoint development
- Enhanced error handling and logging
- Performance optimization

### Long-term Roadmap
- Real-time collaboration features
- Advanced matching algorithms
- Machine learning integration
- Multi-tenant support
- Mobile application development

---

This architecture provides a solid foundation for taxonomic data validation while maintaining security, scalability, and maintainability principles.