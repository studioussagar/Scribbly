from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.db.models import Q

from blog.utils import create_notification
from ..models import Conversation, Message
from ..forms import MessageForm
from django.contrib.auth import get_user_model
from django.http import JsonResponse

User = get_user_model()

@method_decorator(csrf_protect, name='dispatch')
class InboxView(LoginRequiredMixin, generic.TemplateView):
    template_name = 'inbox.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx['conversations'] = Conversation.objects.filter(
            Q(user1=user) | Q(user2=user)
        ).select_related('user1', 'user2').prefetch_related('messages').order_by('-updated_at')
        return ctx

@method_decorator(csrf_protect, name='dispatch')
class MessageUserView(LoginRequiredMixin, generic.FormView):
    form_class = MessageForm
    template_name = 'message.html' 

    def dispatch(self, request, *args, **kwargs):
        self.target_user = get_object_or_404(User, username=kwargs['target_username'])
        users = sorted([request.user, self.target_user], key=lambda u: u.id)
        convo, _ = Conversation.objects.get_or_create(user1=users[0], user2=users[1])
        self.conversation = convo
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax') == '1':
            last_id = request.GET.get('last_id', 0)
            try:
                last_id = int(last_id)
            except ValueError:
                last_id = 0
                
            from django.utils import timezone
            new_msgs = self.conversation.messages.filter(id__gt=last_id).order_by('created_at')
            data = []
            for m in new_msgs:
                local_dt = timezone.localtime(m.created_at)
                data.append({
                    'id': m.id,
                    'text': m.text,
                    'sender': m.sender.username,
                    'created_at': local_dt.strftime('%H:%M')
                })
            return JsonResponse({'messages': data})
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **ctx):
        ctx = super().get_context_data(**ctx)
        user = self.request.user
        ctx['conversations'] = Conversation.objects.filter(
            Q(user1=user) | Q(user2=user)
        ).select_related('user1', 'user2').prefetch_related('messages').order_by('-updated_at')
        ctx['conversation'] = self.conversation
        ctx['messages'] = self.conversation.messages.order_by('created_at')
        ctx['other_user'] = self.target_user
        ctx['other_user_online'] = (self.target_user.profile.is_online)
        return ctx

    def form_valid(self, form):
        print("Message notification block reached")
        msg = form.save(commit=False)
        msg.conversation = self.conversation
        msg.sender = self.request.user
        msg.save()
        # Determine recipient
        recipient = (
            self.conversation.user2
    if self.request.user == self.conversation.user1
    else self.conversation.user1
)
        print("Message notification block reached")
        create_notification(
        recipient=recipient,
        actor=self.request.user,
    notification_type="message",
    text=f"{self.request.user.username} sent you a message.",
        link=reverse(
        "profiles:message_user",
        kwargs={
            "target_username": self.request.user.username
        }
    )
        )
        
        # Ensure created_at is populated and synchronized
        msg.refresh_from_db()
        
        # Touch the conversation to update ordering
        self.conversation.updated_at = msg.created_at
        self.conversation.save(update_fields=['updated_at'])
        
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest' or self.request.GET.get('ajax') == '1':
            from django.utils import timezone
            local_dt = timezone.localtime(msg.created_at)
            return JsonResponse({
                'ok': True,
                'msg': {
                    'id': msg.id,
                    'text': msg.text,
                    'sender': msg.sender.username,
                    'created_at': local_dt.strftime('%H:%M')
                }
            })
            
        return redirect('profiles:message_user', target_username=self.kwargs['target_username'])

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': form.errors})
        return super().form_invalid(form)
    
@csrf_protect
@login_required
@require_POST
def mark_read(request, pk):
    convo = get_object_or_404(Conversation, pk=pk)
    if request.user not in convo.participants():
        return JsonResponse({"error": "forbidden"}, status=403)
    Message.objects.filter(conversation=convo, is_read=False).exclude(sender=request.user).update(is_read=True)
    return JsonResponse({"ok": True})
