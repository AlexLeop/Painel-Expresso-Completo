import getpass
import os
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
            required=False,
            help=(
                "Compatibilidade apenas. Prefira PLATFORM_ADMIN_PASSWORD ou o "
                "prompt interativo para não expor a senha no histórico."
            ),
        )
        parser.add_argument(
            "--password-env",
            type=str,
            default="PLATFORM_ADMIN_PASSWORD",
            help="Nome da variável de ambiente que contém a senha inicial.",
        )

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        name = options["name"].strip()
        password = options.get("password") or os.environ.get(options["password_env"])

        if not password:
            try:
                password = getpass.getpass("Senha segura do administrador: ")
            except (EOFError, KeyboardInterrupt) as exc:
                raise CommandError(
                    "Senha não fornecida. Configure PLATFORM_ADMIN_PASSWORD "
                    "temporariamente ou execute o comando em terminal interativo."
                ) from exc

        if len(password) < 10:
            raise CommandError("A senha deve ter pelo menos 10 caracteres.")

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
