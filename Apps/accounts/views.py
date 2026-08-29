from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView

from Apps.accounts.forms import EmailLoginForm, CustomUserCreationForm


class EmailLoginView(LoginView):
    template_name = 'accounts/login_page.html'
    authentication_form = EmailLoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('home')


class RegisterView(CreateView):
    template_name = 'accounts/register_page.html'
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


def logout_view(request):
    logout(request)
    return redirect('login')