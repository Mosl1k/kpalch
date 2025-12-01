"""
Тесты для приложения shopping_list
"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import Category, ShoppingItem, Friendship, SharedList, UserProfile


class ShoppingListAPITestCase(TestCase):
    """Тесты для API списков покупок"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        UserProfile.objects.create(user=self.user, yandex_id='12345')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Создаем категорию
        self.category = Category.objects.create(
            name='купить',
            display_name='Купить',
            created_by=self.user
        )
    
    def test_list_items_empty(self):
        """Тест получения пустого списка"""
        response = self.client.get('/api/list', {'category': 'купить'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
    
    def test_add_item(self):
        """Тест добавления элемента"""
        response = self.client.post('/api/add', {
            'name': 'Молоко',
            'category': 'купить',
            'priority': 2
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ShoppingItem.objects.count(), 1)
        self.assertEqual(ShoppingItem.objects.first().name, 'Молоко')
    
    def test_buy_item(self):
        """Тест отметки элемента как купленного"""
        item = ShoppingItem.objects.create(
            user=self.user,
            name='Хлеб',
            category=self.category,
            priority=2
        )
        response = self.client.put(f'/api/buy/{item.name}', {
            'bought': True,
            'category': 'купить'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertTrue(item.bought)
    
    def test_delete_item(self):
        """Тест удаления элемента"""
        item = ShoppingItem.objects.create(
            user=self.user,
            name='Масло',
            category=self.category,
            priority=2
        )
        response = self.client.delete(f'/api/delete/{item.name}', {'category': 'купить'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ShoppingItem.objects.count(), 0)
    
    def test_add_category(self):
        """Тест добавления категории"""
        response = self.client.post('/api/category/add', {
            'name': 'работа',
            'display_name': 'Работа'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Category.objects.filter(name='работа').exists())


class FriendsAPITestCase(TestCase):
    """Тесты для API друзей"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        UserProfile.objects.create(user=self.user1, yandex_id='11111')
        UserProfile.objects.create(user=self.user2, yandex_id='22222')
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.user1)
    
    def test_send_friend_request(self):
        """Тест отправки запроса на дружбу"""
        response = self.client.post('/api/friend-request', {
            'user_id': self.user2.id
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Friendship.objects.filter(
            from_user=self.user1,
            to_user=self.user2,
            status='pending'
        ).exists())
    
    def test_accept_friend_request(self):
        """Тест принятия запроса на дружбу"""
        friendship = Friendship.objects.create(
            from_user=self.user2,
            to_user=self.user1,
            status='pending'
        )
        response = self.client.post(f'/api/friend-request/{friendship.id}/accept', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        friendship.refresh_from_db()
        self.assertEqual(friendship.status, 'accepted')
    
    def test_list_friends(self):
        """Тест получения списка друзей"""
        Friendship.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            status='accepted'
        )
        response = self.client.get('/api/friends')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class SharedListAPITestCase(TestCase):
    """Тесты для API шаринга списков"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        UserProfile.objects.create(user=self.user1, yandex_id='11111')
        UserProfile.objects.create(user=self.user2, yandex_id='22222')
        
        # Создаем дружбу
        Friendship.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            status='accepted'
        )
        
        # Создаем категорию и элементы
        self.category = Category.objects.create(
            name='купить',
            display_name='Купить',
            created_by=self.user1
        )
        ShoppingItem.objects.create(
            user=self.user1,
            name='Молоко',
            category=self.category,
            priority=2
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.user1)
    
    def test_share_list(self):
        """Тест отправки списка другу"""
        response = self.client.post('/api/share-list', {
            'user_id': self.user2.id,
            'category': 'купить',
            'message': 'Вот мой список'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(SharedList.objects.filter(
            from_user=self.user1,
            to_user=self.user2,
            category=self.category
        ).exists())
    
    def test_accept_shared_list(self):
        """Тест принятия шаринга списка"""
        shared_list = SharedList.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            category=self.category,
            status='pending'
        )
        
        client2 = APIClient()
        client2.force_authenticate(user=self.user2)
        response = client2.post(f'/api/shared-list/{shared_list.id}/accept', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        shared_list.refresh_from_db()
        self.assertEqual(shared_list.status, 'accepted')
        # Проверяем что элементы скопировались
        self.assertTrue(ShoppingItem.objects.filter(
            user=self.user2,
            name='Молоко',
            category=self.category
        ).exists())


class BulkDeleteTestCase(TestCase):
    """Тесты для массового удаления"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        UserProfile.objects.create(user=self.user, yandex_id='12345')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        self.category = Category.objects.create(
            name='купить',
            display_name='Купить',
            created_by=self.user
        )
        
        # Создаем несколько элементов
        for i in range(5):
            ShoppingItem.objects.create(
                user=self.user,
                name=f'Товар {i}',
                category=self.category,
                priority=2,
                bought=True
            )
    
    def test_bulk_delete(self):
        """Тест массового удаления купленных элементов"""
        items = ShoppingItem.objects.filter(user=self.user, category=self.category)
        initial_count = items.count()
        
        # Удаляем все элементы по одному (как в фронтенде)
        for item in items:
            response = self.client.delete(f'/api/delete/{item.name}', {'category': 'купить'})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(ShoppingItem.objects.filter(user=self.user, category=self.category).count(), 0)

