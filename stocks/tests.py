from django.test import TestCase
from .models import Broker

class BrokerModelTest(TestCase):

    def setUp(self):
        self.broker = Broker.objects.create(
            name="Test Broker",
            code="TB123",
            total_amount=10000.00,
            free_amount=5000.00
        )

    def test_broker_creation(self):
        self.assertEqual(self.broker.name, "Test Broker")
        self.assertEqual(self.broker.code, "TB123")
        self.assertEqual(self.broker.total_amount, 10000.00)
        self.assertEqual(self.broker.free_amount, 5000.00)

    def test_broker_str(self):
        self.assertEqual(str(self.broker), "Test Broker")