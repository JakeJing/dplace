from django.conf.urls import patterns, url, include
from django.shortcuts import redirect
from django.views.generic.base import RedirectView

from rest_framework import routers
from dplace_app import api_views

router = routers.DefaultRouter()
router.register(r'variables', api_views.EAVariableDescriptionViewSet)
router.register(r'codes', api_views.EAVariableCodeDescriptionViewSet)
router.register(r'values', api_views.EAVariableValueViewSet)
router.register(r'societies', api_views.SocietyViewSet)
router.register(r'environmentals', api_views.EnvironmentalViewSet)
router.register(r'isocodes', api_views.ISOCodeViewSet)
router.register(r'language_classes', api_views.LanguageClassViewSet)
router.register(r'language_families', api_views.LanguageFamilyViewSet)
router.register(r'language_classifications', api_views.LanguageClassificationViewSet)
router.register(r'languages', api_views.LanguageViewSet)

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browseable API.

urlpatterns = patterns('dplace_app.views',
	url(r'^$', RedirectView.as_view(url='search_geo/'), name='home'),
	url(r'^search_geo/$', 'search_geo', name='search_geo'),
	url(r'^society/(?P<society_id>\d+)/$', 'view_society', name='view_society'),
    url(r'^angular/$', 'angular', name='angular'),
	# API
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^api/v1/', include(router.urls)),
)


