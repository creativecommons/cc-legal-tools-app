from os.path import dirname, join
import dotenv


def load_env():
    "Get the path to the .env file and load it."
    project_dir = dirname(dirname(__file__))
    dotenv.read_dotenv(join(project_dir, '.env'))
