from django.conf import settings

def department_slugs(request):
    return {'DEPARTMENT_SLUGS': settings.DEPARTMENT_SLUGS}
