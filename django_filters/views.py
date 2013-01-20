from __future__ import unicode_literals

# from django.http import Http404
# from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ImproperlyConfigured
from django.views.generic import View
from django.views.generic.list import MultipleObjectMixin
from django.views.generic.list import MultipleObjectTemplateResponseMixin

from django_filters.filterset import filterset_factory


class FilterMixin(object):
    """
    A mixin that provides a way to show and handle a FilterSet in a request.
    """
    filterset_class = None

    def get_filterset_class(self):
        """
        Returns the filterset class to use in this view
        """
        if self.filterset_class:
            return self.filterset_class
        elif self.model:
            return filterset_factory(self.model)
        else:
            msg = "'%s' must define 'filterset_class' or 'model'"
            raise ImproperlyConfigured(msg % self.__class__.__name__)

    def get_filterset(self, filterset_class):
        """
        Returns an instance of the filterset to be used in this view.
        """
        kwargs = self.get_filterset_kwargs(filterset_class)
        return filterset_class(**kwargs)

    def get_filterset_kwargs(self, filterset_class):
        """
        Returns the keyword arguments for instanciating the filterset.
        """
        kwargs = {'data': self.request.GET or None}
        try:
            kwargs.update({
                'queryset': self.get_queryset(),
            })
        except ImproperlyConfigured:
            # ignore the error here if the filterset has a model defined
            # to acquire a queryset from
            if filterset_class._meta.model is None:
                msg = ("'%s' does not define a 'model' and the view '%s' does "
                       "not return a valid queryset from 'get_queryset'.  You "
                       "must fix one of them.")
                raise ImproperlyConfigured(msg % self.__class__.__name__)
        return kwargs


class BaseFilterView(FilterMixin, MultipleObjectMixin, View):

    def get(self, request, *args, **kwargs):
        filterset_class = self.get_filterset_class()
        self.filterset = self.get_filterset(filterset_class)
        self.object_list = self.filterset.qs
        # allow_empty = self.get_allow_empty()
        # if not allow_empty and len(self.object_list) == 0:
        #     msg = _("Empty list and '%(class_name)s.allow_empty' is False.")
        #     raise Http404(msg % {'class_name': self.__class__.__name__})
        context = self.get_context_data(filter=self.filterset,
                                        object_list=self.object_list)
        return self.render_to_response(context)


class FilterView(MultipleObjectTemplateResponseMixin, BaseFilterView):
    """
    Render some list of objects with filter, set by `self.model` or
    `self.queryset`.
    `self.queryset` can actually be any iterable of items, not just a queryset.
    """
    template_name_suffix = '_filter'


def object_filter(request, model=None, queryset=None, template_name=None,
                  extra_context=None, context_processors=None,
                  filter_class=None):
    class ECFilterView(FilterView):
        """Handle the extra_context from the functional object_filter view"""
        def get_context_data(self, **kwargs):
            context = super(ECFilterView, self).get_context_data(**kwargs)
            extra_context = self.kwargs.get('extra_context') or {}
            for k,v in extra_context.items():
                if callable(v):
                    v = v()
                context[k] = v
            return context

    kwargs = dict(model=model, queryset=queryset, template_name=template_name,
                  filterset_class=filter_class)
    view = ECFilterView.as_view(**kwargs)
    return view(request, extra_context=extra_context)
