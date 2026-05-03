from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'languages', views.LanguageViewSet)
router.register(r'health-scores', views.HealthScoreViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('tree/', views.tree_view, name='tree'),
]
