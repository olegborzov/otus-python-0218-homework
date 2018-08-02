#!/usr/bin/env bash
# Шаги:
# 1. Константы для проекта
# 2. Обновление системы, установка нужных пакетов
# 3. Установка пакетов python из requirements.txt
# 4. Запуск, настройка PostgreSQL: создание юзера и БД
# 5. Подготовка Django - миграции, сборка статик файлов
# 6. Настройка UWSGI
# 7. Настройка nginx
# 8. Запуск nginx

# Project settings
PROJECT_NAME=hasker
PROJECT_FOLDER=$(pwd)
SECRET_KEY="$(openssl rand -base64 50)"

# Postgres settings
DB_NAME=$PROJECT_NAME
DB_USER=$PROJECT_NAME
DB_PASSWORD=Hasker1234


echo "1. Try to update/upgrade repositories..."
apt-get -qq -y update
apt-get -qq -y upgrade


echo "2. Try to install required packages..."
PACKAGES=('nginx' 'postgresql' 'python3' 'python-pip3')
for pkg in "${PACKAGES[@]}"
do
    echo "Installing '$pkg'..."
    apt-get -qq -y install $pkg
    if [ $? -ne 0 ]; then
        echo "Error installing system packages '$pkg'"
        exit 1
    fi
done


echo "3. Try to install Python3 project dependencies..."
pip3 install --upgrade pip
pip3 install -r requirements/production.txt


echo "4. Try to setup PostgreSQL..."
service postgresql start
su postgres -c "psql -c \"CREATE USER ${DB_USER} PASSWORD '${DB_PASSWORD}'\""
su postgres -c "psql -c \"CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}\""


echo "5. Prepare Django..."
python3 manage.py collectstatic
python3 manage.py makemigrations
python3 manage.py migrate


echo "6. Configure uwsgi..."
mkdir -p /run/uwsgi
mkdir -p /usr/local/etc

cat > /usr/local/etc/uwsgi.ini << EOF
[uwsgi]
project = $PROJECT_NAME
chdir = $PROJECT_FOLDER
module = hasker.wsgi:application

master = true
processes = 5

logto = /var/log/$PROJECT_NAME.log

socket = /run/uwsgi/%(project).sock
chmod-socket = 666
vacuum = true

die-on-term = true
env=DJANGO_SETTINGS_MODULE=hasker.settings.production
env=SECRET_KEY=$SECRET_KEY
env=DB_NAME=$DB_NAME
env=DB_USER=$DB_USER
env=DB_PASSWORD=$DB_PASSWORD
EOF


echo "7. Configure nginx..."
cat > /etc/nginx/conf.d/${PROJECT_NAME}.conf << EOF
server {
    listen 8000;
    server_name localhost 127.0.0.1;
    location /static/ {
        root /var/www;
    }
    location /media/ {
        root /var/www;
    }
    location / {
        include uwsgi_params;
        uwsgi_pass unix:/run/uwsgi/${PROJECT_NAME}.sock;
    }
}
EOF


echo "8. Start nginx..."
uwsgi --ini /usr/local/etc/uwsgi.ini &
service nginx start