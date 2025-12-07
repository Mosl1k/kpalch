# Generated migration for SharedListConnection model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('shopping_list', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SharedListConnection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shared_connections', to='shopping_list.category', verbose_name='Категория')),
                ('owner_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owned_shared_lists', to=settings.AUTH_USER_MODEL, verbose_name='Владелец списка')),
                ('shared_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shared_list_connections', to=settings.AUTH_USER_MODEL, verbose_name='Участник')),
            ],
            options={
                'verbose_name': 'Подключение к общему списку',
                'verbose_name_plural': 'Подключения к общим спискам',
                'unique_together': {('owner_user', 'shared_user', 'category')},
            },
        ),
        migrations.AddIndex(
            model_name='sharedlistconnection',
            index=models.Index(fields=['owner_user', 'category'], name='shopping_li_owner_u_category_idx'),
        ),
        migrations.AddIndex(
            model_name='sharedlistconnection',
            index=models.Index(fields=['shared_user', 'category'], name='shopping_li_shared__category_idx'),
        ),
    ]
