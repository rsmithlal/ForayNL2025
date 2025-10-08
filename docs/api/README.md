# API Documentation

## Overview

The ForayNL2025 Django application currently provides a web-based interface for taxonomic matching and review. While the application does not yet implement a formal REST API, this document outlines the current endpoints and provides a framework for future API development.

## Current HTTP Endpoints

### Web Interface Endpoints

#### Dashboard
- **URL**: `/`
- **Method**: `GET`
- **Description**: Main dashboard showing match statistics and navigation
- **Parameters**: None
- **Response**: HTML dashboard page with match counts and links

#### Match Browser
- **URL**: `/matches/{category}/`
- **Method**: `GET`
- **Description**: Browse matches by category
- **Parameters**:
  - `category`: Match category (all_match, mismatch, perfect_myco, mismatch_myco)
- **Response**: HTML page with paginated match list

#### Match Detail
- **URL**: `/detail/{foray_id}/`
- **Method**: `GET`
- **Description**: Detailed view of a specific match
- **Parameters**:
  - `foray_id`: Unique foray specimen identifier
- **Response**: HTML page with match details and MycoBank information

#### Review Form
- **URL**: `/review/{foray_id}/`
- **Methods**: `GET`, `POST`
- **Description**: Form for reviewing and validating matches
- **Parameters**:
  - `foray_id`: Unique foray specimen identifier
- **GET Response**: HTML form for review
- **POST Body**:
  ```json
  {
    "validated_name": "Agaricus campestris L.",
    "reviewer_name": "Expert Mycologist"
  }
  ```
- **POST Response**: Redirect to success page or form with errors

#### Export CSV
- **URL**: `/export/csv/`
- **Method**: `GET`
- **Description**: Export reviewed matches as CSV
- **Parameters**: None
- **Response**: CSV file download with reviewed match data

#### Admin Interface
- **URL**: `/admin/`
- **Method**: `GET`
- **Description**: Django admin interface
- **Parameters**: Requires admin authentication
- **Response**: Admin dashboard for data management

## Data Models API Reference

### ForayFungi2023
Represents original foray collection data.

```json
{
  "foray_id": "F2023-001",
  "genus_and_species_org_entry": "Agaricus campestris",
  "genus_and_species_conf": "Agaricus campestris L.", 
  "genus_and_species_foray_name": "Agaricus campestris (meadow mushroom)"
}
```

### MycoBankList
Represents MycoBank taxonomic reference data.

```json
{
  "mycobank_id": "MB123456",
  "taxon_name": "Agaricus campestris",
  "current_name": "Agaricus campestris L.",
  "authors": "L.",
  "year": "1753",
  "hyperlink": "https://www.mycobank.org/page/Name%20details%20page/123456"
}
```

### ForayMatch
Represents matching results between foray name variants.

```json
{
  "foray_id": "F2023-001",
  "org_entry": "Agaricus campestris",
  "conf_name": "Agaricus campestris L.",
  "foray_name": "Agaricus campestris (meadow mushroom)",
  "match_category": "MATCH_ORG_CONF"
}
```

**Match Categories**:
- `ALL_MATCH`: All three names identical
- `MATCH_ORG_CONF`: org_entry matches conf_name
- `MATCH_ORG_FORAY`: org_entry matches foray_name
- `MATCH_CONF_FORAY`: conf_name matches foray_name
- `ALL_DIFFERENT`: All names different

### ForayPerfectMycoMatch
Represents perfect matches with MycoBank records.

```json
{
  "foray_id": "F2023-001",
  "matched_name": "Agaricus campestris",
  "mycobank_id": "MB123456",
  "mycobank_name": "Agaricus campestris L."
}
```

### ForayMismatchMycoScores
Represents similarity scores for mismatched records.

```json
{
  "foray_id": "F2023-001",
  "org_score": 0.95,
  "conf_score": 0.98,
  "foray_score": 0.85,
  "mycobank_id": "MB123456",
  "mycobank_name": "Agaricus campestris L.",
  "mycobank_expl": "CONF → UPDATED"
}
```

### ReviewedMatch
Represents expert review and validation results.

```json
{
  "foray_id": "F2023-001",
  "org_entry": "Agaricus campestris",
  "conf_name": "Agaricus campestris L.",
  "foray_name": "Agaricus campestris (meadow mushroom)",
  "validated_name": "Agaricus campestris L.",
  "reviewer_name": "Dr. Jane Smith",
  "status": "REVIEWED",
  "reviewed_at": "2023-10-08T14:30:00Z"
}
```

**Status Values**:
- `REVIEWED`: Validation complete
- `PENDING`: Awaiting review
- `SKIPPED`: Temporarily bypassed

## FastAPI Integration Endpoints

The separate FastAPI server provides integration endpoints for automated processing.

### Drive Callback
- **URL**: `/drive-callback`
- **Method**: `POST`
- **Description**: Handles Google Drive push notifications
- **Headers**: 
  - `x-goog-channel-id`: Google notification channel ID
- **Response**:
  ```json
  {"status": "accepted"}
  ```

### Manual Trigger
- **URL**: `/manual-trigger`
- **Method**: `POST`
- **Description**: Manually trigger processing pipeline
- **Response**:
  ```json
  {"status": "triggered"}
  ```

### Health Check
- **URL**: `/health`
- **Method**: `GET`
- **Description**: Service health status
- **Response**:
  ```json
  {"status": "healthy"}
  ```

## Future REST API Design

### Proposed API Endpoints

#### Authentication
```
POST /api/auth/login/
POST /api/auth/logout/
POST /api/auth/refresh/
GET  /api/auth/user/
```

#### Matches
```
GET    /api/matches/                    # List all matches
GET    /api/matches/{foray_id}/         # Get specific match
GET    /api/matches/category/{category}/ # Filter by category
POST   /api/matches/                    # Create new match (admin)
PUT    /api/matches/{foray_id}/         # Update match (admin)
DELETE /api/matches/{foray_id}/         # Delete match (admin)
```

#### Reviews
```
GET    /api/reviews/                    # List all reviews
GET    /api/reviews/{foray_id}/         # Get specific review
POST   /api/reviews/                    # Submit new review
PUT    /api/reviews/{foray_id}/         # Update review
DELETE /api/reviews/{foray_id}/         # Delete review
GET    /api/reviews/status/{status}/    # Filter by status
```

#### Export
```
GET /api/export/csv/                    # Export CSV
GET /api/export/json/                   # Export JSON
GET /api/export/xlsx/                   # Export Excel
```

#### Statistics
```
GET /api/stats/dashboard/               # Dashboard statistics
GET /api/stats/matches/                 # Match statistics
GET /api/stats/reviews/                 # Review statistics
```

### API Implementation Example

```python
# views/api.py (Future implementation)
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import ForayMatch, ReviewedMatch
from .serializers import ForayMatchSerializer, ReviewedMatchSerializer


class ForayMatchViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoints for foray matches."""
    
    queryset = ForayMatch.objects.all()
    serializer_class = ForayMatchSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'foray_id'
    
    def get_queryset(self):
        """Filter matches by category if specified."""
        queryset = ForayMatch.objects.all()
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(match_category=category)
        return queryset
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get list of available match categories."""
        categories = ForayMatch.objects.values_list(
            'match_category', flat=True
        ).distinct()
        return Response({'categories': list(categories)})
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get match statistics."""
        stats = {}
        for category in ForayMatch.objects.values_list(
            'match_category', flat=True
        ).distinct():
            stats[category] = ForayMatch.objects.filter(
                match_category=category
            ).count()
        return Response(stats)


class ReviewedMatchViewSet(viewsets.ModelViewSet):
    """API endpoints for reviewed matches."""
    
    queryset = ReviewedMatch.objects.all()
    serializer_class = ReviewedMatchSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'foray_id'
    
    def get_queryset(self):
        """Filter reviews by status if specified."""
        queryset = ReviewedMatch.objects.all()
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get all pending reviews."""
        pending = ReviewedMatch.objects.filter(status='PENDING')
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        """Export reviewed matches as CSV."""
        from django.http import HttpResponse
        import csv
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="reviews.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Foray ID', 'Validated Name', 'Reviewer', 'Status', 'Reviewed At'
        ])
        
        for review in ReviewedMatch.objects.filter(status='REVIEWED'):
            writer.writerow([
                review.foray_id,
                review.validated_name,
                review.reviewer_name,
                review.status,
                review.reviewed_at.isoformat()
            ])
        
        return response
```

### API Serializers Example

```python
# serializers.py (Future implementation)
from rest_framework import serializers
from .models import ForayMatch, ReviewedMatch, ForayPerfectMycoMatch


class ForayMatchSerializer(serializers.ModelSerializer):
    """Serializer for ForayMatch model."""
    
    class Meta:
        model = ForayMatch
        fields = [
            'foray_id', 'org_entry', 'conf_name', 
            'foray_name', 'match_category'
        ]
        read_only_fields = ['foray_id']


class ReviewedMatchSerializer(serializers.ModelSerializer):
    """Serializer for ReviewedMatch model."""
    
    class Meta:
        model = ReviewedMatch
        fields = [
            'foray_id', 'org_entry', 'conf_name', 'foray_name',
            'validated_name', 'reviewer_name', 'status', 'reviewed_at'
        ]
        read_only_fields = ['foray_id', 'reviewed_at']
    
    def validate_validated_name(self, value):
        """Validate the validated name field."""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError(
                "Validated name cannot be empty."
            )
        return value.strip()
    
    def validate_reviewer_name(self, value):
        """Validate the reviewer name field."""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError(
                "Reviewer name cannot be empty."
            )
        return value.strip()


class ForayPerfectMycoMatchSerializer(serializers.ModelSerializer):
    """Serializer for ForayPerfectMycoMatch model."""
    
    mycobank_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ForayPerfectMycoMatch
        fields = [
            'foray_id', 'matched_name', 'mycobank_id', 
            'mycobank_name', 'mycobank_url'
        ]
    
    def get_mycobank_url(self, obj):
        """Generate MycoBank URL for the record."""
        return f"https://www.mycobank.org/page/Name%20details%20page/{obj.mycobank_id}"
```

### API Authentication

```python
# authentication.py (Future implementation)
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response


class CustomAuthToken(ObtainAuthToken):
    """Custom authentication token endpoint."""
    
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email,
            'username': user.username
        })
```

### API URL Configuration

```python
# urls.py (Future implementation)
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.api import ForayMatchViewSet, ReviewedMatchViewSet
from .authentication import CustomAuthToken

router = DefaultRouter()
router.register(r'matches', ForayMatchViewSet)
router.register(r'reviews', ReviewedMatchViewSet)

api_patterns = [
    path('auth/login/', CustomAuthToken.as_view(), name='api_token_auth'),
    path('', include(router.urls)),
]

urlpatterns = [
    # Web interface URLs
    path('', include('core.urls')),
    # API URLs
    path('api/v1/', include(api_patterns)),
]
```

## Error Handling

### HTTP Status Codes

- **200 OK**: Successful GET request
- **201 Created**: Successful POST request  
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server error

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "validated_name": ["This field is required."],
      "reviewer_name": ["This field is required."]
    }
  }
}
```

## Rate Limiting

Future API implementation should include rate limiting:

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}
```

## API Documentation

Future API should include interactive documentation:

```python
# Install drf-spectacular
pip install drf-spectacular

# settings.py
INSTALLED_APPS = [
    'drf_spectacular',
]

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# urls.py
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
```

---

This API documentation provides both current endpoint information and a roadmap for future REST API development, ensuring consistent and well-documented access to the ForayNL2025 taxonomic matching system.