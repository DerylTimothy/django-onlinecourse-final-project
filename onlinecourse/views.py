from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Choice, Course, Enrollment, Question, Submission


def index(request):
    """Menampilkan daftar semua kursus."""
    courses = Course.objects.all()
    return render(
        request,
        "onlinecourse/course_list_bootstrap.html",
        {"course_list": courses},
    )


def course_details(request, course_id):
    """Menampilkan detail kursus beserta soal ujiannya."""
    course = get_object_or_404(Course, pk=course_id)
    return render(
        request,
        "onlinecourse/course_details_bootstrap.html",
        {"course": course},
    )


def extract_answers(request):
    """Mengambil daftar ID choice yang dipilih dari form POST."""
    submitted_answers = []
    for key in request.POST:
        if key.startswith("choice"):
            values = request.POST.getlist(key)
            for val in values:
                try:
                    choice_id = int(val)
                    if choice_id not in submitted_answers:
                        submitted_answers.append(choice_id)
                except (TypeError, ValueError):
                    continue
    return submitted_answers


@login_required
def submit(request, course_id):
    """Menyimpan jawaban ujian user ke Submission lalu mengarahkan ke halaman hasil."""
    course = get_object_or_404(Course, pk=course_id)
    enrollment = get_object_or_404(Enrollment, user=request.user, course=course)

    submission = Submission.objects.create(enrollment=enrollment)
    choice_ids = extract_answers(request)

    if choice_ids:
        selected_choices = Choice.objects.filter(id__in=choice_ids)
        submission.choices.add(*selected_choices)

    return redirect(
        "onlinecourse:show_exam_result",
        course_id=course.id,
        submission_id=submission.id,
    )


@login_required
def show_exam_result(request, course_id, submission_id):
    """Menghitung skor dan menampilkan halaman hasil ujian."""
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(Submission, pk=submission_id)

    selected_choices = submission.choices.all()
    selected_ids = list(selected_choices.values_list("id", flat=True))

    total_score = 0
    max_score = 0

    for question in course.question_set.all():
        question_grade = getattr(question, "grade", 0)
        max_score += question_grade

        if hasattr(question, "is_get_score") and callable(question.is_get_score):
            if question.is_get_score(selected_ids):
                total_score += question_grade
        else:
            correct_ids = set(
                question.choice_set.filter(is_correct=True).values_list("id", flat=True)
            )
            chosen_ids = set(
                selected_choices.filter(question=question).values_list("id", flat=True)
            )
            if chosen_ids and chosen_ids == correct_ids:
                total_score += question_grade

    context = {
        "course": course,
        "submission": submission,
        "selected_ids": selected_ids,
        "grade": total_score,
        "max_score": max_score,
    }

    return render(request, "onlinecourse/exam_result_bootstrap.html", context)