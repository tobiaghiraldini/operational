from __future__ import annotations

from django import forms

from apps.workflows.models import Workflow


class WorkflowCreateForm(forms.ModelForm):
    """Dashboard: create a workflow with name, category, and optional description."""

    class Meta:
        model = Workflow
        fields = ("name", "category", "description")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3, "class": "w-full"}),
            "name": forms.TextInput(attrs={"class": "w-full"}),
            "category": forms.Select(attrs={"class": "w-full"}),
        }

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Name is required.")
        return name
