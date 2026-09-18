from django.shortcuts import redirect, get_object_or_404
from django.views import generic
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from ..models import Post, Category
from ..forms import BlogCreateForm
from ..utils import sanitize_html
from review_center.models import WriterApplication


@method_decorator(csrf_protect, name='dispatch')
class BlogCreate(LoginRequiredMixin, generic.CreateView):
    model = Post
    form_class = BlogCreateForm
    template_name = 'create_blog.html'
    success_url = reverse_lazy('home_view')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['author'] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = self.request.user
        form.instance.author = user
        print("RAW CONTENT")
        print(form.cleaned_data.get("content"))
        form.instance.content = sanitize_html(form.cleaned_data.get('content', ''))
        if user.is_author:
            form.instance.status = form.cleaned_data.get('status')
        else:
            form.instance.status = 2
        messages.success(self.request, "Your blog has been published successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context

@method_decorator(csrf_protect, name='dispatch')
class ViewerBlogTry(LoginRequiredMixin, generic.CreateView):
    model = Post
    form_class = BlogCreateForm
    template_name = 'create_blog.html'
    success_url = reverse_lazy('home_view')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['author'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.content = sanitize_html(form.cleaned_data.get('content', ''))
        form.instance.status = 2  # pending review

        response =super().form_valid(form)

        WriterApplication.objects.get_or_create(
        user=self.request.user,
        preview_blog=self.object,
        defaults={
            "status": "pending"
        },
        submitted_title = self.object.title,
        submitted_content = self.object.content
    )
        messages.success(
            self.request,
            "Your blog has been submitted for review! If it resonates, you'll be given access to become an Author."
        )
        return response

    def form_invalid(self, form):
        print(form.errors)
        return super().form_invalid(form)

    def dispatch(self, request, *args, **kwargs):
        # Guard: is_author raises AttributeError on AnonymousUser — check auth first
        if request.user.is_authenticated and request.user.is_author:
            return redirect('create_blog')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context


class PostEditView(LoginRequiredMixin, UserPassesTestMixin, generic.edit.UpdateView):
    model = Post
    form_class = BlogCreateForm
    template_name = 'create_blog.html'
    success_url = reverse_lazy('dashboard')

    def get_object(self, queryset=None):
        return get_object_or_404(Post, slug=self.kwargs['slug'], author=self.request.user)

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['author'] = self.request.user
        return kwargs

    def form_valid(self, form):
        print("RAW CONTENT")
        print(form.cleaned_data.get("content"))
        form.instance.content = sanitize_html(form.cleaned_data.get("content", ""))
        cleaned = sanitize_html(form.cleaned_data.get("content", ""))
        print("SANITIZED CONTENT")
        print(cleaned)
        messages.success(self.request, "Post updated successfully!")
        response = super().form_valid(form)

        print("AFTER SAVE")
        print(self.object.content)

        return response
