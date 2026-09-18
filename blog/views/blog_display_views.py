
from django.views import generic
from ..models import Post, Category
from django.db.models import Q

class BlogHome(generic.ListView):
    template_name = 'home.html'
    queryset = Post.objects.filter(status=1).order_by('-date_created')[:5]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['featured_post'] = Post.objects.filter(status=1).order_by('-date_created').first()
        context['popular_posts'] = Post.objects.filter(status=1).order_by('-date_created')[:3]
        return context

class BlogList(generic.ListView):
    template_name = "blog_list.html"
    context_object_name = "posts"
    paginate_by = 10

    def get_queryset(self):
        qs = (
            Post.objects.filter(status=1)
            .select_related("author")
            .prefetch_related("category")
            .order_by("-date_created")
        )
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(content__icontains=q)
                | Q(author__name__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = Category.objects.all()
        ctx["query"] = self.request.GET.get("q", "").strip()
        return ctx

class BlogView(generic.DetailView):
    model = Post
    template_name = 'blog.html'
    def get_queryset(self):
        return Post.objects.filter(status=1)

class BlogAbout(generic.TemplateView):
    template_name = 'about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tech_stack'] = [
            "Django", "Python", "Bootstrap 5", "JavaScript",
            "WebSockets (Channels)", "TinyMCE", "SQLite", "HTML & CSS"
        ]
        return context


class BlogCategory(generic.ListView):
    model = Post
    template_name = 'category_post.html'
    paginate_by = 10

    def get_queryset(self):
        slug = self.kwargs.get('slug')
        category = Category.objects.filter(slug=slug).first()
        if category:
            return Post.objects.filter(category=category, status=1).order_by('-date_created')
        return Post.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = Category.objects.filter(slug=self.kwargs.get('slug')).first()
        return context

