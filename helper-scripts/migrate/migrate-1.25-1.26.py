"""
Update config to use the database instead of config.py

To upgrade, we need this file and the new configuration manager (which is able
to populate the new database)
"""
import sys
import os
import json
import psycopg2
import psycopg2.extras
import configparser

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "'/../..")

def set_or_create_setting(attribute_name, value, connection, cursor, keep_connection_open=False):
    """
    Insert OR set value for a paramter in the database. ON CONFLICT SET VALUE.

    :return int: number of updated rows
    """
    try:
        value = json.dumps(value)
    except ValueError:
        return None

    try:
        query = 'INSERT INTO fourcat_settings (name, value) Values (%s, %s) ON CONFLICT (name) DO UPDATE SET value = EXCLUDED.value'
        cursor.execute(query, (attribute_name, value))
        updated_rows = cursor.rowcount
        connection.commit()

        if not keep_connection_open:
            connection.close()

    except (Exception, psycopg2.DatabaseError) as error:
        print('Error transfering setting %s with value %s: %s' % (attribute_name, str(value), str(error)))
        updated_rows = None
    finally:
        if connection is not None and not keep_connection_open:
            connection.close()

    return updated_rows

print("  Checking if preexisting config.py file...")
transfer_settings = False
config = None
try:
    import config as old_config
    transfer_settings = True
    print("  ...Yes, prexisting settings exist.")
except (SyntaxError, ImportError) as e:
    print("  ...No prexisting settings exist.")

print("  Checking if fourcat_settings table exists...")
if transfer_settings:
    connection = psycopg2.connect(dbname=old_config.DB_NAME, user=old_config.DB_USER, password=old_config.DB_PASSWORD, host=old_config.DB_HOST, port=old_config.DB_PORT, application_name="4cat-migrate")
else:
    import common.config_manager as config
    connection = psycopg2.connect(dbname=config.get('DB_NAME'), user=config.get('DB_USER'), password=config.get('DB_PASSWORD'), host=config.get('DB_HOST'), port=config.get('DB_PORT'), application_name="4cat-migrate")
cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cursor.execute("SELECT EXISTS (SELECT * from information_schema.tables WHERE table_name=%s)", ('fourcat_settings',))
has_table = cursor.fetchone()
if not has_table["exists"]:
    print("  ...No, adding table fourcat_setttings.")
    cursor.execute("""CREATE TABLE IF NOT EXISTS fourcat_settings (
      name                   TEXT UNIQUE PRIMARY KEY,
      value                  TEXT DEFAULT '{}'
    )""")
    connection.commit()
else:
    print("  ...Yes, fourcat_settings table already exists.")

if transfer_settings:
    print("  Moving settings to database...")
    # FIRST update config_defaults.ini or docker_config.ini
    # Check if Docker
    USING_DOCKER = True
    configfile_to_save = old_config.DOCKER_CONFIG_FILE
    if os.path.exists(old_config.DOCKER_CONFIG_FILE):
      config_reader = configparser.ConfigParser()
      config_reader.read(old_config.DOCKER_CONFIG_FILE)
      if not config_reader['DOCKER'].getboolean('use_docker_config'):
          # Not using docker
          USING_DOCKER = False
          configfile_to_save = 'backend/config_defaults.ini'
          config_reader.read(configfile_to_save)

    # Update DB info
    if not config_reader.has_section('DATABASE'):
        config_reader.add_section('DATABASE')
    if old_config.DB_HOST:
        config_reader['DATABASE']['db_host'] = old_config.DB_HOST
    if old_config.DB_PORT:
        config_reader['DATABASE']['db_port'] = str(old_config.DB_PORT)
    if old_config.DB_USER:
        config_reader['DATABASE']['db_user'] = str(old_config.DB_USER)
    if old_config.DB_PASSWORD:
        config_reader['DATABASE']['db_password'] = str(old_config.DB_PASSWORD)
    if old_config.DB_NAME:
        config_reader['DATABASE']['db_name'] = old_config.DB_NAME

    # Update API info
    if not config_reader.has_section('API'):
        config_reader.add_section('API')
    if old_config.API_HOST:
        config_reader['API']['api_host'] = old_config.API_HOST
    if old_config.API_PORT:
        config_reader['API']['api_port'] = str(old_config.API_PORT)

    # Update PATH info
    if not config_reader.has_section('PATHS'):
        config_reader.add_section('PATHS')
    if old_config.PATH_LOGS:
        config_reader['PATHS']['path_logs'] = old_config.PATH_LOGS
    if old_config.PATH_IMAGES:
        config_reader['PATHS']['path_images'] = old_config.PATH_IMAGES
    if old_config.PATH_DATA:
        config_reader['PATHS']['path_data'] = old_config.PATH_DATA
    if old_config.PATH_LOCKFILE:
        config_reader['PATHS']['path_lockfile'] = old_config.PATH_LOCKFILE
    if old_config.PATH_SESSIONS:
        config_reader['PATHS']['path_sessions'] = old_config.PATH_SESSIONS

    # Update SALT and KEY
    if not config_reader.has_section('GENERATE'):
        config_reader.add_section('GENERATE')
    if old_config.ANONYMISATION_SALT:
        config_reader['GENERATE']['anonymisation_salt'] = str(old_config.ANONYMISATION_SALT)
    if old_config.FlaskConfig.SECRET_KEY:
        config_reader['GENERATE']['secret_key'] = str(old_config.FlaskConfig.SECRET_KEY)

    # Save config file
    with open(configfile_to_save, 'w') as configfile:
        config_reader.write(configfile)

    # UPDATE Database with other settings
    old_settings = [
        ('DATASOURCES', getattr(old_config, "DATASOURCES", False)),
        ('YOUTUBE_API_SERVICE_NAME', getattr(old_config, "YOUTUBE_API_SERVICE_NAME", False)),
        ('YOUTUBE_API_VERSION', getattr(old_config, "YOUTUBE_API_VERSION", False)),
        ('YOUTUBE_DEVELOPER_KEY', getattr(old_config, "YOUTUBE_DEVELOPER_KEY", False)),
        ('TOOL_NAME', getattr(old_config, "TOOL_NAME", False)),
        ('TOOL_NAME_LONG', getattr(old_config, "TOOL_NAME_LONG", False)),
        ('PATH_VERSION', getattr(old_config, "PATH_VERSION", False)),
        ('GITHUB_URL', getattr(old_config, "GITHUB_URL", False)),
        ('EXPIRE_DATASETS', getattr(old_config, "EXPIRE_DATASETS", False)),
        ('EXPIRE_ALLOW_OPTOUT', getattr(old_config, "EXPIRE_ALLOW_OPTOUT", False)),
        ('WARN_INTERVAL', getattr(old_config, "WARN_INTERVAL", False)),
        ('WARN_LEVEL', getattr(old_config, "WARN_LEVEL", False)),
        ('WARN_SLACK_URL', getattr(old_config, "WARN_SLACK_URL", False)),
        ('WARN_EMAILS', getattr(old_config, "WARN_EMAILS", False)),
        ('ADMIN_EMAILS', getattr(old_config, "ADMIN_EMAILS", False)),
        ('MAILHOST', getattr(old_config, "MAILHOST", False)),
        ('MAIL_SSL', getattr(old_config, "MAIL_SSL", False)),
        ('MAIL_USERNAME', getattr(old_config, "MAIL_USERNAME", False)),
        ('MAIL_PASSWORD', getattr(old_config, "MAIL_PASSWORD", False)),
        ('NOREPLY_EMAIL', getattr(old_config, "NOREPLY_EMAIL", False)),
        ('SCRAPE_TIMEOUT', getattr(old_config, "SCRAPE_TIMEOUT", False)),
        ('SCRAPE_PROXIES', getattr(old_config, "SCRAPE_PROXIES", False)),
        ('IMAGE_INTERVAL', getattr(old_config, "IMAGE_INTERVAL", False)),
        ('MAX_EXPLORER_POSTS', getattr(old_config, "MAX_EXPLORER_POSTS", False)),
        # Processor and datasource settings have a different format in new database
        ('image_downloader.MAX_NUMBER_IMAGES', getattr(old_config, "MAX_NUMBER_IMAGES", False)),
        ('image_downloader_telegram.MAX_NUMBER_IMAGES', getattr(old_config, "MAX_NUMBER_IMAGES", False)),
        ('tumblr-search.TUMBLR_CONSUMER_KEY', getattr(old_config, "TUMBLR_CONSUMER_KEY", False)),
        ('tumblr-search.TUMBLR_CONSUMER_SECRET_KEY', getattr(old_config, "TUMBLR_CONSUMER_SECRET_KEY", False)),
        ('tumblr-search.TUMBLR_API_KEY', getattr(old_config, "TUMBLR_API_KEY", False)),
        ('tumblr-search.TUMBLR_API_SECRET_KEY', getattr(old_config, "TUMBLR_API_SECRET_KEY", False)),
        ('get-reddit-votes.REDDIT_API_CLIENTID', getattr(old_config, "REDDIT_API_CLIENTID", False)),
        ('get-reddit-votes.REDDIT_API_SECRET', getattr(old_config, "REDDIT_API_SECRET", False)),
        ('tcat-auto-upload.TCAT_SERVER', getattr(old_config, "TCAT_SERVER", False)),
        ('tcat-auto-upload.TCAT_TOKEN', getattr(old_config, "TCAT_TOKEN", False)),
        ('tcat-auto-upload.TCAT_USERNAME', getattr(old_config, "TCAT_USERNAME", False)),
        ('tcat-auto-upload.TCAT_PASSWORD', getattr(old_config, "TCAT_PASSWORD", False)),
        ('pix-plot.PIXPLOT_SERVER', getattr(old_config, "PIXPLOT_SERVER", False)),
        # FlaskConfig are accessed from old_config slightly differently
        ('FLASK_APP', getattr(old_config.FlaskConfig, "FLASK_APP", False)),
        ('SERVER_NAME', getattr(old_config.FlaskConfig, "SERVER_NAME", False)),
        ('SERVER_HTTPS', getattr(old_config.FlaskConfig, "SERVER_HTTPS", False)),
        ('HOSTNAME_WHITELIST', getattr(old_config.FlaskConfig, "HOSTNAME_WHITELIST", False)),
        ('HOSTNAME_WHITELIST_API', getattr(old_config.FlaskConfig, "HOSTNAME_WHITELIST_API", False)),
        ('HOSTNAME_WHITELIST_NAME', getattr(old_config.FlaskConfig, "HOSTNAME_WHITELIST_NAME", False)),
        ]

    for name, setting in old_settings:
        if setting:
            set_or_create_setting(name, setting, connection=connection, cursor=cursor, keep_connection_open=True)

    print('  Setting migrated to Database!')

# Close database connection
connection.close()

print("  Done!")