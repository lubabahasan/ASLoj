from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from .forms import UserSignupForm, UserLoginForm, ProblemForm, ExampleFormSet
from .models import Problem
from .models import Contest
from .forms import ContestForm
from django.utils import timezone

from django.core.paginator import Paginator
from django.contrib.auth import get_user_model

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


@login_required
def contest_list(request):
    status = request.GET.get('status', '')
    now = timezone.now()
    contests = Contest.objects.all()

    if status == 'upcoming':
        contests = contests.filter(start_time__gt=now)
    elif status == 'running':
        contests = contests.filter(start_time__lte=now, end_time__gte=now)
    elif status == 'finished':
        contests = contests.filter(end_time__lt=now)

    return render(request, 'contests/contest_list.html', {'contests': contests})

@login_required
def contest_detail(request, pk):
    contest = get_object_or_404(Contest, pk=pk)
    return render(request, 'contests/contest_detail.html', {'contest': contest})

@login_required
def contest_create(request):
    # Only allow admin to create contest
    if not request.user.is_staff:
        return redirect('contest_list')

    if request.method == 'POST':
        form = ContestForm(request.POST)
        if form.is_valid():
            contest = form.save(commit=False)
            contest.creator = request.user  # ✅ Add creator properly
            contest.save()
            form.save_m2m()
            return redirect('contest_list')
    else:
        form = ContestForm()  # ✅ Initialize for GET requests

        # ✅ Always return a context that includes 'form'
    return render(request, 'contests/contest_form.html', {'form': form})

@login_required
def contest_update(request, pk):
    contest = get_object_or_404(Contest, pk=pk, creator=request.user)
    if request.method == 'POST':
        form = ContestForm(request.POST, instance=contest)
        if form.is_valid():
            form.save()
            return redirect('contest_detail', pk=pk)
    else:
        form = ContestForm(instance=contest)
    return render(request, 'contests/create_contest.html', {'form': form})

@login_required
def contest_delete(request, pk):
    contest = get_object_or_404(Contest, pk=pk, creator=request.user)
    if request.method == 'POST':
        contest.delete()
        return redirect('contest_list')
    return render(request, 'contests/contest_confirm_delete.html', {'contest': contest})

def contest_detail(request, pk):
    contest = get_object_or_404(Contest, pk=pk)
    return render(request, 'contests/contest_detail.html', {'contest': contest})


User = get_user_model()
def leaderboard_view(request):
    # Get all users ordered by points descending
    users = User.objects.order_by('-points')

    # Pagination: 10 per page
    paginator = Paginator(users, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Find logged-in user rank
    user_rank = None
    if request.user.is_authenticated:
        user_list = list(users.values_list('id', flat=True))
        if request.user.id in user_list:
            user_rank = user_list.index(request.user.id) + 1  # +1 because rank starts from 1

    context = {
        'page_obj': page_obj,
        'user_rank': user_rank
    }
    return render(request, 'leaderboard.html', context)