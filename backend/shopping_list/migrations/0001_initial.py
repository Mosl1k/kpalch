# Generated manually for shopping_list app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='Название')),
                ('display_name', models.CharField(max_length=100, verbose_name='Отображаемое название')),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name='Создано')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_categories', to=settings.AUTH_USER_MODEL, verbose_name='Создатель')),
            ],
            options={
                'verbose_name': 'Категория',
                'verbose_name_plural': 'Категории',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('yandex_id', models.CharField(blank=True, max_length=50, null=True, unique=True, verbose_name='Yandex ID')),
                ('avatar_url', models.URLField(blank=True, null=True, verbose_name='URL аватара')),
                ('date_of_birth', models.DateField(blank=True, null=True, verbose_name='Дата рождения')),
                ('gender', models.CharField(blank=True, choices=[('male', 'Мужской'), ('female', 'Женский'), ('other', 'Другой')], max_length=10, null=True, verbose_name='Пол')),
                ('phone_number', models.CharField(blank=True, max_length=20, null=True, verbose_name='Номер телефона')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Профиль пользователя',
                'verbose_name_plural': 'Профили пользователей',
            },
        ),
        migrations.CreateModel(
            name='ShoppingItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Название')),
                ('bought', models.BooleanField(default=False, verbose_name='Куплено')),
                ('priority', models.IntegerField(choices=[(1, 'Низкий'), (2, 'Средний'), (3, 'Высокий')], default=2, verbose_name='Приоритет')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
                ('order', models.IntegerField(default=0, verbose_name='Порядок')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='shopping_list.category', verbose_name='Категория')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shopping_items', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Элемент списка',
                'verbose_name_plural': 'Элементы списка',
                'ordering': ['order', '-priority', 'name'],
                'unique_together': {('user', 'name', 'category')},
            },
        ),
        migrations.AddIndex(
            model_name='shoppingitem',
            index=models.Index(fields=['user', 'category', 'bought'], name='shopping_li_user_id_category_idx'),
        ),
        migrations.CreateModel(
            name='Friendship',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Ожидает подтверждения'), ('accepted', 'Принято'), ('rejected', 'Отклонено')], default='pending', max_length=10, verbose_name='Статус')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
                ('from_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='friendship_requests_sent', to=settings.AUTH_USER_MODEL, verbose_name='От пользователя')),
                ('to_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='friendship_requests_received', to=settings.AUTH_USER_MODEL, verbose_name='К пользователю')),
            ],
            options={
                'verbose_name': 'Дружба',
                'verbose_name_plural': 'Дружбы',
                'unique_together': {('from_user', 'to_user')},
            },
        ),
        migrations.AddIndex(
            model_name='friendship',
            index=models.Index(fields=['from_user', 'status'], name='shopping_li_from_us_status_idx'),
        ),
        migrations.AddIndex(
            model_name='friendship',
            index=models.Index(fields=['to_user', 'status'], name='shopping_li_to_user_status_idx'),
        ),
        migrations.CreateModel(
            name='SharedList',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Ожидает принятия'), ('accepted', 'Принято'), ('rejected', 'Отклонено')], default='pending', max_length=10, verbose_name='Статус')),
                ('message', models.TextField(blank=True, null=True, verbose_name='Сообщение')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shared_lists', to='shopping_list.category', verbose_name='Категория')),
                ('from_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lists_shared', to=settings.AUTH_USER_MODEL, verbose_name='От пользователя')),
                ('to_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lists_received', to=settings.AUTH_USER_MODEL, verbose_name='К пользователю')),
            ],
            options={
                'verbose_name': 'Шаринг списка',
                'verbose_name_plural': 'Шаринги списков',
                'unique_together': {('from_user', 'to_user', 'category')},
            },
        ),
        migrations.AddIndex(
            model_name='sharedlist',
            index=models.Index(fields=['from_user', 'status'], name='shopping_li_from_us_status2_idx'),
        ),
        migrations.AddIndex(
            model_name='sharedlist',
            index=models.Index(fields=['to_user', 'status'], name='shopping_li_to_user_status2_idx'),
        ),
    ]

