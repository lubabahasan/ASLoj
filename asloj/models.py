from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, User
from django.core.validators import FileExtensionValidator
from django.db import models
from mysite import settings
from django.utils import timezone
from ckeditor.fields import RichTextField

class UserManager(BaseUserManager):
    def create_user(self, email, full_name, university_id, password=None):
        if not email:
            raise ValueError("Email is required")
        if not email.endswith("@uap-bd.edu"):
            raise ValueError("This email is not allowed")

        email = self.normalize_email(email)

        if User.objects.filter(university_id=university_id).exists():
            raise ValueError("This university ID is already taken")

        user = self.model(
            email=email,
            full_name=full_name,
            university_id=university_id
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, full_name, university_id, password=None):
        user = self.create_user(email, full_name, university_id, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser, PermissionsMixin):
    full_name = models.CharField(max_length=200)
    university_id = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    phone = models.CharField(max_length=20, blank=True, null=True)
    points = models.IntegerField(default=0)

    pfp = models.ImageField(
        upload_to='pfp/',
        blank=True,
        null=True,
        default='pfp/default.jpeg',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name", "university_id"]

    objects = UserManager()

    def __str__(self):
        return self.email


class Problem(models.Model):
    problem_id = models.AutoField(primary_key=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='problems')

    title = models.CharField(max_length=255)
    statement = RichTextField()
    input_specification = RichTextField()
    output_specification = RichTextField()
    difficulty = models.CharField(max_length=10, choices=[('Easy', 'Easy'), ('Medium', 'Medium'), ('Hard', 'Hard')],
                                  default='Easy')
    time_limit = models.IntegerField(default=1)  # in seconds

    def __str__(self):
        return f"{self.title}"

def test_input_upload_to(instance, filename):
    return f"problems/{instance.problem.problem_id}/test_inputs/{filename}"

def test_output_upload_to(instance, filename):
    return f"problems/{instance.problem.problem_id}/test_outputs/{filename}"

class TestInput(models.Model):
    problem = models.ForeignKey('Problem', on_delete=models.CASCADE, related_name='test_inputs')
    file = models.FileField(upload_to=test_input_upload_to)

class TestOutput(models.Model):
    problem = models.ForeignKey('Problem', on_delete=models.CASCADE, related_name='test_outputs')
    file = models.FileField(upload_to=test_output_upload_to)


class Example(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='examples')
    input = models.TextField()
    output = models.TextField()
    note = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

class Submission(models.Model):
    id = models.BigAutoField(primary_key=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='submissions')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='submissions')
    code_file = models.FileField(upload_to="submissions/")

    LANGUAGE_CHOICES = [
        ("py", "Python"),
        ("c", "C"),
        ("cpp", "C++"),
        ("java", "Java"),
        ("js", "JavaScript"),
    ]

    STATUS_CHOICES = [
        ("P", "Pending"),
        ("AC", "Accepted"),
        ("WA", "Wrong Answer"),
        ("RE", "Runtime Error"),
        ("TLE", "Time Limit Exceeded"),
    ]

    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="P")

    created_at = models.DateTimeField(auto_now_add=True)


class Contest(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    problems = models.ManyToManyField(Problem, blank=True, related_name='contests')
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_contests')

    def __str__(self):
        return self.name

    def is_active(self):
        now = timezone.now()
        return self.start_time <= now <= self.end_time