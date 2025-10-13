from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Count
from .forms import UserSignupForm, UserLoginForm, ProblemForm, SubmissionForm, ContestForm, ExampleFormSet
from .models import Problem, Submission, Contest, TestInput, TestOutput, Discussion, Comment, User


def signup_view(request):
    if request.method == "POST":
        form = UserSignupForm(request.POST, request.FILES)
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
    # Top 5 users (by points)
    top_users = User.objects.order_by('-points')[:8]

    # Active contests (currently running)
    now = timezone.now()
    upcoming_contests = Contest.objects.filter(start_time__gt=now).order_by('start_time')[:3]
    recent_submissions = Submission.objects.filter(user=request.user).order_by('-created_at')[:3]

    context = {
        'top_users': top_users,
        "upcoming_contests": upcoming_contests,
        'recent_submissions': recent_submissions,
    }
    return render(request, "home.html", context)

def profile_view(request):
    user = request.user
    recent_submissions = Submission.objects.filter(user=user).order_by('-created_at')[:5]  # last 5 submissions
    problem_counts = Problem.objects.filter(submissions__user=user, submissions__status='AC') \
        .values('difficulty') \
        .annotate(count=Count('problem_id'))

    difficulty_stats = {'Easy': 0, 'Medium': 0, 'Hard': 0}
    for entry in problem_counts:
        difficulty_stats[entry['difficulty']] = entry['count']

    max_rating = 1847
    problems_solved = sum(difficulty_stats.values())
    contests_count = 23

    return render(request, "profile.html",{
        'recent_submissions': recent_submissions,
        'difficulty_stats': difficulty_stats,
        'problems_solved': problems_solved,
        'contests_count': contests_count,
        'max_rating': max_rating,
    })

def problems_view(request):
    problems = Problem.objects.all().order_by('problem_id')

    difficulty = request.GET.get('difficulty')
    created_by = request.GET.get('created_by')

    if difficulty:
        problems = problems.filter(difficulty=difficulty)

    if created_by:
        problems = problems.filter(created_by__email__icontains=created_by)

    return render(request, 'problems/problems.html', {'problems': problems})

def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def problem_crud(request, pk=None):
    if pk:
        problem = get_object_or_404(Problem, pk=pk)
    else:
        problem = Problem(created_by=request.user)

    example_form = ExampleFormSet(request.POST or None, instance=problem)

    if request.method == 'POST':
        form = ProblemForm(request.POST, instance=problem)
        if form.is_valid() and example_form.is_valid():
            problem = form.save(commit=False)
            problem.created_by = request.user
            problem.save()
            example_form.instance = problem
            example_form.save()
            return redirect('problems')
    else:
        form = ProblemForm(instance=problem)

    return render(request, 'problems/problem_crud.html', {'form': form, 'formset': example_form})

@login_required
def problem_delete(request, pk):
    problem = get_object_or_404(Problem, pk=pk)
    if problem.created_by == request.user:
        problem.delete()
    return redirect('problems')

@login_required
def problem_detail(request, pk):
    problem = get_object_or_404(Problem, pk=pk)
    submission_form = SubmissionForm(initial={'problem': problem})
    return render(request, 'problems/problem_detail.html', {
        'problem': problem,
        'submission_form': submission_form,
    })


@login_required
def submit_solution(request, pk):
    problem = get_object_or_404(Problem, pk=pk)

    if request.method == 'POST':
        form = SubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.user = request.user
            submission.problem = problem
            submission.save()
            messages.success(request, "Submission uploaded successfully!")
            return redirect('submission_detail', pk=submission.pk)
        else:
            messages.error(request, "There was an error with your submission.")
            return render(request, 'problems/problem_detail.html', {
                'problem': problem,
                'submission_form': form,
            })
    return redirect('problem_detail', pk=problem.pk)

def submission_list(request):
    submissions = Submission.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'submissions/submission_list.html', {'submissions': submissions})

def submission_detail(request, pk):
    submission = get_object_or_404(Submission, pk=pk, user=request.user)

    code_content = ""
    if submission.code_file:
        submission.code_file.open('r')
        code_content = submission.code_file.read()
        submission.code_file.close()

    return render(request, 'submissions/submission_detail.html', {
        'submission': submission,
        'code_content': code_content
    })


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

@login_required
def community_view(request):
    discussions = Discussion.objects.all().order_by('-created_at')

    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")
        if title and content:
            Discussion.objects.create(author=request.user, title=title, content=content)
            return redirect("community")

    return render(request, "community.html", {"discussions": discussions})


@login_required
def discussion_detail(request, discussion_id):
    discussion = get_object_or_404(Discussion, id=discussion_id)
    comments = discussion.comments.all().order_by('created_at')

    if request.method == "POST":
        content = request.POST.get("content")
        if content:
            Comment.objects.create(discussion=discussion, author=request.user, content=content)
            return redirect("discussion_detail", discussion_id=discussion_id)

    return render(request, "discussion_detail.html", {"discussion": discussion, "comments": comments})