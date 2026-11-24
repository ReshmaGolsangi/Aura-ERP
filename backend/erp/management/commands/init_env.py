from django.core.management.base import BaseCommand
from django.core.management.utils import get_random_secret_key
from erp.envfile import read_env, write_env


class Command(BaseCommand):
    help = "Create backend/.env with a private SECRET_KEY if it does not exist yet."

    def handle(self, *a, **o):
        env = read_env()
        if "SECRET_KEY" not in env:
            env["SECRET_KEY"] = get_random_secret_key()
            write_env(env)
            self.stdout.write("Created private settings file.")
