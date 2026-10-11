from django.contrib import admin

from .models import Question, QuestionnaireResponse, QuestionSection, ResponseFile


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ("display_order", "code", "qtype", "text", "is_active")


@admin.register(QuestionSection)
class QuestionSectionAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "handled_by", "display_order", "is_active")
    list_editable = ("display_order", "is_active")
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("code", "text", "qtype", "section", "display_order", "is_active")
    list_filter = ("section", "qtype", "is_active")
    search_fields = ("code", "text")


class ResponseFileInline(admin.TabularInline):
    model = ResponseFile
    extra = 0
    fields = ("question_code", "kind", "name", "size", "created_at")
    readonly_fields = fields
    can_delete = False


@admin.register(QuestionnaireResponse)
class QuestionnaireResponseAdmin(admin.ModelAdmin):
    list_display = ("display_name", "status", "answered_count", "question_count", "updated_at")
    list_filter = ("status",)
    search_fields = ("school_name",)
    readonly_fields = ("data", "answered_count", "question_count", "created_at", "updated_at")
    inlines = [ResponseFileInline]
