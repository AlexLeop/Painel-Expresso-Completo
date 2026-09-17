import uuid
from django.core.management.base import BaseCommand, CommandError
from accounts.models import PlatformAdmin


class Command(BaseCommand):
    help = "Cria ou atualiza um Administrador Soberano da Plataforma (PlatformAdmin/Superadmin)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            type=str,
            required=True,
            help="Email institucional do Administrador Soberano",
        )
        parser.add_argument(
            "--name",
            type=str,
            default="Administrador Soberano",
            help="Nome do Administrador Soberano",
        )
        parser.add_argument(
            "--password",
            type=str,
            required=True,
            help="Senha de acesso segura",
        )

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        name = options["name"].strip()
        password = options["password"]

        if not password:
            raise CommandError("A senha não pode ser vazia.")

        admin, created = PlatformAdmin.objects.get_or_create(
            email=email,
            defaults={
                "id": uuid.uuid4(),
                "name": name,
            },
        )

        admin.name = name
        admin.set_password(password)
        admin.save()

        action_desc = "criado com sucesso" if created else "atualizado com sucesso"
        self.stdout.write(
            self.style.SUCCESS(
                f"PlatformAdmin '{email}' (ID: {admin.id}) {action_desc} com soberania total sobre a plataforma."
            )
        )
