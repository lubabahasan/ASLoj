from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from .forms import UserSignupForm, UserLoginForm, ProblemForm, ExampleFormSet
from .models import Problem

def signup_view(request):
    if request.method == "POST":
        form = UserSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()
            login(request, user)
            return redirect("home")
    else:
        form = UserSignupForm()
    return render(request, "signup.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("home")
    else:
        form = UserLoginForm()
    return render(request, "login.html", {"form": form})

@login_required
def home_view(request):
    return render(request, "home.html")

def profile_view(request):
    return render(request, "profile.html")

def problems_view(request):
    problems = Problem.objects.all()

    difficulty = request.GET.get('difficulty')
    created_by = request.GET.get('created_by')

    if difficulty:
        problems = problems.filter(difficulty=difficulty)

    if created_by:
        problems = problems.filter(created_by__email__icontains=created_by)

    return render(request, 'problems.html', {'problems': problems})

def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def problem_crud(request, pk=None):
    if pk:
        problem = get_object_or_404(Problem, pk=pk)
    else:
        problem = Problem(created_by=request.user)

    if request.method == 'POST':
        form = ProblemForm(request.POST, instance=problem)
        formset = ExampleFormSet(request.POST, instance=problem)
        if form.is_valid() and formset.is_valid():
            problem = form.save(commit=False)
            problem.created_by = request.user
            problem.save()
            formset.save()
            return redirect('problem_detail', pk=problem.pk)
    else:
        form = ProblemForm(instance=problem)
        formset = ExampleFormSet(instance=problem)

    return render(request, 'problem_crud.html', {'form': form, 'formset': formset})

@login_required
def problem_delete(request, pk):
    problem = get_object_or_404(Problem, pk=pk)
    if problem.created_by == request.user:
        problem.delete()
    return redirect('problems')

def problem_detail(request, pk):
    problem = get_object_or_404(Problem, pk=pk)
    return render(request, 'problem_detail.html', {'problem': problem})

