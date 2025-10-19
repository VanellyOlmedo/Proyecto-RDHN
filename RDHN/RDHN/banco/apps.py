from django.apps import AppConfig


class BancoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'banco'
    verbose_name = 'Sistema Bancario'
    
    def ready(self):
        """Se ejecuta cuando la app está lista"""
        # Registrar signals
        import banco.signals