from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Count
from .forms import UserSignupForm, UserLoginForm, ProblemForm, SubmissionForm, ContestForm, ExampleFormSet, ContestSubmissionForm
import os
from django.conf import settings
from .models import Problem, Submission, Contest, TestInput, TestOutput, Discussion, ContestSubmission, Comment, User, Group, \
    GroupInvitation, ContestRegistration
from .utils import check_submission
from time import localtime


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

    ac_problem_ids = (
        Submission.objects
        .filter(user=user, status='AC')
        .values_list('problem', flat=True)
        .distinct()
    )

    problem_counts = (
        Problem.objects
        .filter(problem_id__in=ac_problem_ids)
        .values('difficulty')
        .annotate(count=Count('problem_id'))
    )

    difficulty_stats = {'Easy': 0, 'Medium': 0, 'Hard': 0}
    for entry in problem_counts:
        difficulty = entry.get('difficulty')
        cnt = entry.get('count', 0)
        if difficulty in difficulty_stats:
            difficulty_stats[difficulty] = cnt

    problems_solved = sum(difficulty_stats.values())
    users = User.objects.order_by('-points')
    user_rank = None
    user_list = list(users.values_list('id', flat=True))
    if user.id in user_list:
        user_rank = user_list.index(user.id) + 1

    contests_count = 2
    max_rating = user.points

    return render(request, "profile.html",{
        'recent_submissions': recent_submissions,
        'difficulty_stats': difficulty_stats,
        'problems_solved': problems_solved,
        'contests_count': contests_count,
        'max_rating': max_rating,
        'user_rank': user_rank,
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

    if request.method == 'POST':
        form = ProblemForm(request.POST, instance=problem)
        formset = ExampleFormSet(request.POST, request.FILES, instance=problem)

        if form.is_valid() and formset.is_valid():
            problem = form.save(commit=False)
            problem.created_by = request.user
            problem.save()
            formset.save()

            for f in request.FILES.getlist('test_inputs'):
                TestInput.objects.create(problem=problem, file=f)

            for f in request.FILES.getlist('test_outputs'):
                TestOutput.objects.create(problem=problem, file=f)

            return redirect('problems')
    else:
        form = ProblemForm(instance=problem)
        formset = ExampleFormSet(instance=problem)

    return render(request, 'problems/problem_crud.html', {'form': form, 'formset': formset})

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

            results = check_submission(problem, submission.code_file.path, submission.language, problem.time_limit)

            if any(r["verdict"] == "TLE" for r in results):
                submission.status = "TLE"
            elif any(r["verdict"] == "RE" for r in results):
                submission.status = "RE"
            elif any(r["verdict"] == "CE" for r in results):
                submission.status = "Compilation Error"
            elif any(r["verdict"] == "WA" for r in results):
                submission.status = "WA"
            else:
                submission.status = "AC"
            submission.save()

            code_content = ""
            if submission.code_file:
                # submission.code_file.open('r')
                # try:
                #     code_content = submission.code_file.read()
                #     if isinstance(code_content, bytes):
                #         code_content = code_content.decode('utf-8', errors='replace')
                # finally:
                #     submission.code_file.close()
                with open(submission.code_file.path, "r", encoding="utf-8", errors="replace") as f:
                    code_content = f.read()

            return render(request, 'submissions/submission_detail.html', {
                'submission': submission,
                'results': results,
                'code_content': code_content
            })

        else:
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
def contest_detail(request, contest_id):
    contest = get_object_or_404(Contest, id=contest_id)
    registrations = ContestRegistration.objects.filter(contest=contest)
    user_registered = registrations.filter(user=request.user).exists()
    total_registered = registrations.count()

    now = localtime()

    context = {
        "contest": contest,
        "registrations": registrations,
        "user_registered": user_registered,
        "total_registered": total_registered,
        "now": now,
    }
    return render(request, "contests/contest_detail.html", context)

@login_required
def start_contest(request, contest_id):
    contest = get_object_or_404(Contest, id=contest_id)
    now = timezone.now()

    # Check contest start time
    if now < contest.start_time:
        messages.warning(request, "You need to wait until the contest starts!")
        return redirect('contest_detail', contest_id=contest.id)

    # Check contest end time
    if now > contest.end_time:
        messages.warning(request, "This contest has already ended.")
        return redirect('contest_detail', contest_id=contest.id)

    # All good, render start contest page
    return render(request, 'contests/start_contest.html', {'contest': contest})

@login_required
def contest_create(request):
    # Only allow admin to create contest
    if not request.user.is_staff:
        return redirect('contest_list')

    if request.method == 'POST':
        form = ContestForm(request.POST)
        if form.is_valid():
            contest = form.save(commit=False)
            contest.creator = request.user
            contest.save()
            form.save_m2m()
            return redirect('contest_list')
    else:
        form = ContestForm()

    return render(request, 'contests/contest_form.html', {'form': form})

@login_required
def contest_update(request, contest_id):
    contest = get_object_or_404(Contest, pk=contest_id, creator=request.user)
    if request.method == 'POST':
        form = ContestForm(request.POST, instance=contest)
        if form.is_valid():
            form.save()
            return redirect('contest_detail', contest_id=contest_id)
    else:
        form = ContestForm(instance=contest)
    return render(request, 'contests/create_contest.html', {'form': form})

@login_required
def contest_delete(request, contest_id):
    contest = get_object_or_404(Contest, pk=contest_id, creator=request.user)
    if request.method == 'POST':
        contest.delete()
        return redirect('contest_list')
    return redirect('contest_list')

@login_required
def contest_register(request, contest_id):
    contest = get_object_or_404(Contest, id=contest_id)

    # Collect user info from custom user model
    registration, created = ContestRegistration.objects.get_or_create(
        contest=contest,
        user=request.user,
        defaults={
            'name': getattr(request.user, 'full_name', 'Anonymous'),
            'email': getattr(request.user, 'email', ''),
            'student_id': getattr(request.user, 'university_id', ''),
        }
    )

    return redirect('contest_registered', contest_id=contest.id)

@login_required
def contest_registered(request, contest_id):
    contest = get_object_or_404(Contest, id=contest_id)
    registration = ContestRegistration.objects.filter(contest=contest, user=request.user).first()

    return render(request, 'contests/contest_registered.html', {
        'contest': contest,
        'registration': registration
    })

@login_required
def contest_problems(request, contest_id):
    contest = get_object_or_404(Contest, id=contest_id)
    now = timezone.now()

    # Contest timing message
    if now < contest.start_time:
        message = "The contest hasn't started yet."
    elif now > contest.end_time:
        message = "The contest has ended."
    else:
        message = "Contest is running!"

    problems = contest.problems.all()

    # Get latest submission status for each problem for the current user
    problem_status = {}
    problem_status = {}
    for problem in problems:
        latest_submission = Submission.objects.filter(
            user=request.user,
            problem=problem
        ).order_by('-created_at').first()

        problem_status[problem.problem_id] = latest_submission.status if latest_submission else "—"

    context = {
        'contest': contest,
        'message': message,
        'problems': problems,
        'problem_status': problem_status,
    }
    return render(request, 'contests/contest_problems.html', context)

@login_required
def submit_contest_solution(request, contest_id, problem_id):
    contest = get_object_or_404(Contest, id=contest_id)
    problem = get_object_or_404(Problem, problem_id=problem_id)

    if request.method == 'POST':
        form = ContestSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.user = request.user
            submission.problem = problem
            submission.contest = contest
            submission.save()
            messages.success(request, "Submission uploaded successfully!")
            return redirect('contest_problems', contest_id=contest.id)
        else:
            messages.error(request, "There was an error with your submission.")
    else:
        form = ContestSubmissionForm()

    return render(request, 'contests/contest_problem_detail.html', {
        'contest': contest,
        'problem': problem,
        'form': form,
    })

@login_required
def contest_problem_detail(request, contest_id, problem_id):
    contest = get_object_or_404(Contest, id=contest_id)
    problem = get_object_or_404(Problem, problem_id=problem_id)
    submission_form = ContestSubmissionForm()

    if request.method == 'POST':
        submission_form = ContestSubmissionForm(request.POST, request.FILES)
        if submission_form.is_valid():
            # Save the submission without committing yet
            submission = submission_form.save(commit=False)
            submission.user = request.user
            submission.contest = contest
            submission.problem = problem
            submission.save()  # save to DB

            # Redirect to contest submission detail page
            return redirect('contests/contest_submission_detail', contest_id=contest.id, submission_id=submission.id)


    context = {
        'contest': contest,
        'problem': problem,
        'submission_form': submission_form,
    }
    return render(request, 'contests/contest_problem_detail.html', context)

@login_required
def contest_submission_detail(request, contest_id, submission_id):
    contest = get_object_or_404(Contest, id=contest_id)
    submission = get_object_or_404(ContestSubmission, id=submission_id, contest=contest)

    # Load code content
    code_content = ""
    if submission.code_file:
        submission.code_file.open()
        code_content = submission.code_file.read().decode('utf-8')
        submission.code_file.close()

    # Example: if you have a function to get test case results
    # Replace with your actual test case evaluation logic
    results = getattr(submission, 'test_results', None)  # list of dicts with input, expected, actual, stderr, verdict

    context = {
        'contest': contest,
        'submission': submission,
        'code_content': code_content,
        'results': results,
    }
    return render(request, 'contests/contest_submission_detail.html', context)

@login_required
def contest_submission_list(request, contest_id):
    contest = get_object_or_404(Contest, id=contest_id)
    submissions = Submission.objects.filter(contest=contest, user=request.user).order_by("-created_at")

    context = {
        "contest": contest,
        "submissions": submissions,
    }
    return render(request, "contests/contest_submission_list.html", context)

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


@login_required
def create_group(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            group = Group.objects.create(name=name, created_by=request.user)
            group.members.add(request.user)
            messages.success(request, "Group created successfully!")
            return redirect('group_list')
    return render(request, 'groups/create_group.html')

@login_required
def group_detail(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    members = group.members.all()
    is_creator = group.created_by == request.user
    return render(request, 'groups/group_detail.html', {
        'group': group,
        'members': members,
        'is_creator': is_creator,
    })

@login_required
def group_list(request):
    user_groups = request.user.user_groups.all()
    invitations = GroupInvitation.objects.filter(invited_user=request.user, status='PENDING')
    return render(request, 'groups/group_list.html', {
        'user_groups': user_groups,
        'invitations': invitations,
    })


@login_required
def invite_member(request, group_id):
    # Fetch the group
    group = get_object_or_404(Group, id=group_id)

    # Check if the user is a member
    if request.user not in group.members.all():
        messages.error(request, "You must be a member to invite others.")
        return redirect('group_list')

    if request.method == 'POST':
        email = request.POST.get('email')
        invited_user = User.objects.filter(email=email).first()

        if invited_user:
            if invited_user in group.members.all():
                messages.warning(request, f"{invited_user.full_name} is already a member.")
            else:
                GroupInvitation.objects.get_or_create(
                    group=group,
                    invited_user=invited_user,
                    invited_by=request.user
                )
                messages.success(request, f"Invitation sent to {email}")
        else:
            messages.error(request, "No user found with that email.")

        return redirect('group_detail', group_id=group.id)

    return render(request, 'groups/invite_member.html', {'group': group})

@login_required
def respond_invitation(request, invitation_id, action):
    invitation = get_object_or_404(GroupInvitation, id=invitation_id, invited_user=request.user)

    if action == 'accept':
        invitation.status = 'ACCEPTED'
        invitation.group.members.add(request.user)
        messages.success(request, f"You joined {invitation.group.name}")
    elif action == 'decline':
        invitation.status = 'DECLINED'
        messages.info(request, "Invitation declined.")

    invitation.save()
    return redirect('group_list')


@login_required
def leave_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    group.members.remove(request.user)
    messages.info(request, f"You left {group.name}")
    return redirect('group_list')

@login_required
def delete_group(request, group_id):
    group = get_object_or_404(Group, id=group_id, created_by=request.user)
    group.delete()
    messages.success(request, "Group deleted successfully.")
    return redirect('group_list')

@login_required
def remove_member(request, group_id, user_id):
    group = get_object_or_404(Group, id=group_id, created_by=request.user)
    user_to_remove = get_object_or_404(User, id=user_id)
    group.members.remove(user_to_remove)
    messages.info(request, f"{user_to_remove.full_name} removed from {group.name}")
    return redirect('group_detail', group_id=group.id)