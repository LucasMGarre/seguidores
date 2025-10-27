import asyncio
import requests
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class PaymentManager:
    def __init__(self, api_key, api_url):
        self.api_key = api_key
        self.api_url = api_url
        self.pending_payments = {}  # {transaction_id: {user_id, amount, created_at}}
        
    def create_pix_payment(self, amount, user_id, description, cpf='00000000000'):
        """Cria um pagamento PIX na LiraPay"""
        headers = {
            "api-secret": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "total_amount": amount,
            "payment_method": "PIX",
            "external_id": f"telegram_{user_id}_{int(datetime.now().timestamp())}",
            "webhook_url": "https://seu-webhook.com/callback",  # Configure seu webhook aqui
            "items": [{
                "id": "1",
                "title": description,
                "description": description,
                "price": amount,
                "quantity": 1,
                "is_physical": False
            }],
            "ip": "0.0.0.0",
            "customer": {
                "name": f"Usuario_{user_id}",
                "email": f"user{user_id}@telegram.bot",
                "phone": "00000000000",
                "document_type": "CPF",
                "document": cpf
            }
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/v1/transactions", 
                json=payload, 
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200 or response.status_code == 201:
                data = response.json()
                # Guarda informação do pagamento pendente
                self.pending_payments[data['id']] = {
                    'user_id': user_id,
                    'amount': amount,
                    'created_at': datetime.now()
                }
                return data
            else:
                logger.error(f"Erro ao criar pagamento: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Exceção ao criar pagamento: {e}")
            return None
        
    def check_payment_status(self, transaction_id):
        """Verifica status do pagamento"""
        headers = {"api-secret": self.api_key}
        
        try:
            response = requests.get(
                f"{self.api_url}/v1/transactions/{transaction_id}", 
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Erro ao verificar status: {e}")
            return None

    async def monitor_pending_payments(self, callback_on_paid):
        """Monitora pagamentos pendentes a cada 30 segundos"""
        while True:
            try:
                current_time = datetime.now()
                to_remove = []
                
                for transaction_id, payment_info in list(self.pending_payments.items()):
                    # Remove pagamentos pendentes após 24 horas
                    if current_time - payment_info['created_at'] > timedelta(hours=24):
                        to_remove.append(transaction_id)
                        continue
                    
                    status = self.check_payment_status(transaction_id)
                    if status and status.get('status') == 'AUTHORIZED':
                        # Pagamento confirmado! Chama o callback
                        await callback_on_paid(
                            payment_info['user_id'],
                            transaction_id,
                            payment_info['amount']
                        )
                        to_remove.append(transaction_id)
                
                # Remove transações processadas ou expiradas
                for transaction_id in to_remove:
                    self.pending_payments.pop(transaction_id, None)
                    
            except Exception as e:
                logger.error(f"Erro no monitor de pagamentos: {e}")
                
            # Espera 30 segundos antes da próxima verificação
            await asyncio.sleep(30)