# Hasker: Poor Man's Stackoverflow
Q&A analog of stackoverflow on Django 2.0

### Requirements
<ul>
    <li>Python 3</li>
    <li>Django 2.0</li>
    <li>PostgreSQL</li>
</ul>
<b>Python packages</b>:
<ul>
    <li>django-debug-toolbar (on development)</li>
    <li>psycopg2 (on production)</li>
    <li>django-crispy-forms</li>
    <li>django-rest-swagger</li>
    <li>djangorestframework-simplejwt</li>
    <li>Pillow</li>
</ul>

### Prepare
```
apt-get update
apt-get upgrade
apt-get install -y git
```

### Build
```
cd hasker
make prod
```
