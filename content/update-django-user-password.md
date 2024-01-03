Title: Update Django user password
Author: Nekrasov Pavel
Date: 2023-09-02 15:00
Category: Blog
Tags: python, django
Slug: update-django-user-password
Summary: Update Django user password from shell.

## Update Django user password from shell

Enter Django Shell

```bash 
python manage.py shell
```

Update password

```python
from django.contrib.auth.models import User

users = User.objects.all() 

print(users)

user = users[0]

user.set_password('123')
user.save()
```

If you are using custom user model
```python
from your_app.auth.models import User

users = User.objects.all() 

print(users)

user = users[0]

user.set_password('123')
user.save()
```
