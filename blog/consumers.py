import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Conversation, Message

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        self.user = self.scope['user']

        # Verify authentication status
        if not self.user.is_authenticated:
            await self.close()
            return

        # Secure: Ensure user physically belongs to the conversation scope
        is_participant = await self.is_participant(self.user.id, self.conversation_id)
        if not is_participant:
            await self.close()
            return

        # Bind websocket connection to a generalized room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group asynchronously 
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive stringified JSON from the connected JavaScript socket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_text = text_data_json.get('message', '').strip()

        if not message_text:
            return

        # Process standard database insertion through asynchronous adapters
        msg = await self.save_message(self.user.id, self.conversation_id, message_text)
        if not msg:
            return

        # Distribute the valid model data to all participants actively connected
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'id': msg['id'],
                'message': msg['text'],
                'sender': msg['sender'],
                'created_at': msg['created_at']
            }
        )

    # Secondary layer: Catch the group broadcast and return it straight to the individual sockets
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'id': event['id'],
            'message': event['message'],
            'sender': event['sender'],
            'created_at': event['created_at']
        }))

    @database_sync_to_async
    def is_participant(self, user_id, conversation_id):
        try:
            convo = Conversation.objects.get(id=conversation_id)
            return user_id in [convo.user1_id, convo.user2_id]
        except Conversation.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, user_id, conversation_id, text):
        try:
            convo = Conversation.objects.get(id=conversation_id)
            msg = Message.objects.create(
                conversation=convo,
                sender_id=user_id,
                text=text
            )
            # Ensure auto_now_add fields are populated in memory
            msg.refresh_from_db()
            
            # Cascade updated_at timestamps to push chats to the top of inbox lists
            convo.save(update_fields=['updated_at'])
            
            # Format time explicitly aware to the active application zone setup
            local_dt = timezone.localtime(msg.created_at)
            
            return {
                'id': msg.id,
                'text': msg.text,
                'sender': msg.sender.username,
                'created_at': local_dt.strftime('%H:%M')
            }
        except Exception as e:
            print(f"Channels Data Intercept Error: {e}")
            import traceback
            traceback.print_exc()
            return None
