import json
import re
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Prefetch
from nexus import NexusReader
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from serializers import *
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.permissions import AllowAny
from rest_framework.views import Response
from rest_framework.renderers import JSONRenderer
from filters import *
from renderers import DPLACECsvRenderer, ZipRenderer


# Resource routes
class VariableDescriptionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VariableDescriptionSerializer
    filter_fields = ('label', 'name', 'index_categories', 'niche_categories', 'source')
    queryset = VariableDescription.objects.all()

    # Override retrieve to use the detail serializer, which includes categories
    def retrieve(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = VariableDescriptionDetailSerializer(self.object)
        return Response(serializer.data)


class VariableCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VariableCategorySerializer
    filter_fields = ('name', 'index_variables', 'niche_variables',)
    queryset = VariableCategory.objects.all()
    # Override retrieve to use the detail serializer, which includes variables

    def retrieve(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = VariableCategoryDetailSerializer(self.object)
        return Response(serializer.data)


class VariableCodeDescriptionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VariableCodeDescriptionSerializer
    filter_fields = ('variable',)
    queryset = VariableCodeDescription.objects.all()


class VariableCodedValueViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VariableCodedValueSerializer
    filter_fields = ('variable', 'coded_value', 'code', 'society',)
    # Avoid additional database trips by select_related for foreign keys
    queryset = VariableCodedValue.objects.select_related('variable').select_related('code').all()


class SocietyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SocietySerializer
    queryset = Society.objects.all().select_related(
        'source', 'language__iso_code', 'language__glotto_code', 'language__family')


class ISOCodeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ISOCodeSerializer
    filter_fields = ('iso_code',)
    queryset = ISOCode.objects.all()


class GlottoCodeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = GlottoCodeSerializer
    filter_fields = ('glotto_code',)
    queryset = GlottoCode.objects.all()


class EnvironmentalCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EnvironmentalCategorySerializer
    filter_fields = ('name',)
    queryset = EnvironmentalCategory.objects.all()


class EnvironmentalVariableViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EnvironmentalVariableSerializer
    filter_fields = ('name', 'category', 'units',)
    queryset = EnvironmentalVariable.objects.all()


class EnvironmentalValueViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EnvironmentalValueSerializer
    filter_fields = ('variable', 'environmental',)
    queryset = EnvironmentalValue.objects.all()


class EnvironmentalViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EnvironmentalSerializer
    filter_fields = ('society', 'iso_code',)
    queryset = Environmental.objects.all()


class LanguageViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LanguageSerializer
    filter_fields = ('name', 'iso_code', 'societies', 'family',)
    queryset = Language.objects.all()


class LanguageFamilyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LanguageFamilySerializer
    filter_fields = ('name', 'scheme',)
    queryset = LanguageFamily.objects.all()


class TreeResultsSetPagination(PageNumberPagination):
    """
    Since trees may have *many* languages, which are serialized as well, we limit the
    page size to just 1.
    """
    page_size = 1
    page_size_query_param = 'page_size'
    max_page_size = 10


class LanguageTreeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LanguageTreeSerializer
    filter_fields = ('name',)
    queryset = LanguageTree.objects.all()
    pagination_class = TreeResultsSetPagination


class SourceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SourceSerializer
    filter_fields = ('author', 'name')
    queryset = Source.objects.all()


# returns trees that contain the societies from the SocietyResultSet
# maybe needs cleaning up in the future
def trees_from_languages_array(language_ids):
    from ete2 import Tree
    trees = LanguageTree.objects\
        .filter(languages__pk__in=language_ids)\
        .prefetch_related(
            'languages__family', 'languages__glotto_code', 'languages__iso_code')\
        .distinct()
    for t in trees:
        if 'glotto' in t.name:
            langs_in_tree = [str(l.glotto_code.glotto_code)
                             for l in t.languages.all() if l.id in language_ids]
        else:
            langs_in_tree = [str(l.iso_code.iso_code)
                             for l in t.languages.all() if l.id in language_ids]
        newick = Tree(t.newick_string, format=1)
        try:
            if 'glotto' not in t.name:
                newick.prune(langs_in_tree, preserve_branch_length=True)
                t.newick_string = newick.write(format=1)
            else:
                # kind of hacky, but needed for when langs_in_tree is only 1
                # in future, maybe exclude these trees from the search results?
                if len(langs_in_tree) == 1:
                    node = newick.search_nodes(name=langs_in_tree[0])
                    if len(node[0].get_leaves()) > 1:
                        t.newick_string = "(%s:1);" % (langs_in_tree[0])
                    elif (len(node[0].get_leaves()) == 1) \
                            and not (node[0].get_leaves()[0].name == langs_in_tree[0]):
                        t.newick_string = "(%s:1);" % (langs_in_tree[0])
                    else:
                        newick.prune(langs_in_tree, preserve_branch_length=True)
                        t.newick_string = newick.write(format=1)
                else:
                    newick.prune(langs_in_tree, preserve_branch_length=True)
                    t.newick_string = newick.write(format=1)
        except:
            continue
    return trees


def result_set_from_query_dict(query_dict):
    result_set = SocietyResultSet()
    # Criteria keeps track of what types of data were searched on, so that we can
    # AND them together
    criteria = []

    if 'language_classifications' in query_dict:
        criteria.append(SEARCH_LANGUAGE)
        classifications = query_dict['language_classifications']
        for classification in classifications:
            language_ids = [int(classification['id'])]
            languages = Language.objects.filter(pk__in=language_ids)  # Returns a queryset
            languages.select_related('societies')
            for language in languages:
                for society in language.societies.all():
                    result_set.add_language(society, language)

    if 'variable_codes' in query_dict:
        criteria.append(SEARCH_VARIABLES)
        ids = [x['id'] for x in query_dict['variable_codes'] if 'id' in x]

        variables = {
            v.id: v for v in VariableDescription.objects
            .filter(id__in=[x['variable'] for x in query_dict['variable_codes']])
            .prefetch_related(Prefetch(
                'codes', queryset=VariableCodeDescription.objects.filter(id__in=ids)))
        }

        for x in query_dict['variable_codes']:
            variable = variables[x['variable']]
            assert set(ids) == set(c.id for c in variable.codes.all())

            if variable.data_type and variable.data_type.lower() == 'continuous':
                values = VariableCodedValue.objects.filter(variable__id=x['variable'])
                if 'min' in x:
                    values = values\
                        .exclude(coded_value='NA')\
                        .filter(coded_value__gt=x['min']).filter(coded_value__lt=x['max'])
                else:  # NA selected
                    values.filter(coded_value=x['code'])
            else:
                coded_value_ids = []
                # Aggregate all the coded values for each selected code
                for code in variable.codes.all():
                    coded_value_ids.extend(
                        code.variablecodedvalue_set.values_list('id', flat=True))
                values = VariableCodedValue.objects.filter(id__in=coded_value_ids)

            for value in values\
                    .select_related('society__language__family') \
                    .select_related('society__language__iso_code')\
                    .select_related('society__language__glotto_code') \
                    .select_related('society__source')\
                    .prefetch_related('references'):
                result_set.add_cultural(value.society, variable, variable.codes, value)

    if 'environmental_filters' in query_dict:
        criteria.append(SEARCH_ENVIRONMENTAL)
        environmental_filters = query_dict['environmental_filters']
        # There can be multiple filters, so we must aggregate the results.
        for environmental_filter in environmental_filters:
            values = EnvironmentalValue.objects\
                .filter(variable=environmental_filter['id'])

            operator = environmental_filter['operator']
            if operator == 'inrange':
                values = values\
                    .filter(value__gt=environmental_filter['params'][0])\
                    .filter(value__lt=environmental_filter['params'][1])
            elif operator == 'outrange':
                values = values\
                    .filter(value__gt=environmental_filter['params'][1])\
                    .filter(value__lt=environmental_filter['params'][0])
            elif operator == 'gt':
                values = values.filter(value__gt=environmental_filter['params'][0])
            elif operator == 'lt':
                values = values.filter(value__lt=environmental_filter['params'][0])
            values = values.select_related(
                'variable', 'environmental__society__language')
            # get the societies from the values
            for value in values:
                result_set.add_environmental(value.society(), value.variable, value)

    if 'geographic_regions' in query_dict:
        criteria.append(SEARCH_GEOGRAPHIC)
        geographic_region_ids = [int(x['id']) for x in query_dict['geographic_regions']]
        regions = GeographicRegion.objects.filter(pk__in=geographic_region_ids)
        for region in regions:
            for society in Society.objects\
                    .filter(location__intersects=region.geom)\
                    .select_related(
                        'language__family',
                        'language__glotto_code',
                        'language__iso_code')\
                    .prefetch_related('source').all():
                result_set.add_geographic_region(society, region)
    # Filter the results to those that matched all criteria
    result_set.finalize(criteria)
    
    # search for language trees
    language_ids = []
    for s in result_set.societies:
        if s.society.language:
            language_ids.append(s.society.language.id)
    trees = trees_from_languages_array(language_ids)
    for t in trees:
        result_set.add_language_tree(t)

    return result_set


@api_view(['POST'])
@permission_classes((AllowAny,))
def find_societies(request):
    """
    View to find the societies that match an input request.  Currently expects
    { language_filters: [{language_ids: [1,2,3]}], variable_codes: [4,5,6...],
    environmental_filters: [{id: 1, operator: 'gt', params: [0.0]},
    {id:3, operator 'inrange', params: [10.0,20.0] }] }

    Returns serialized collection of SocietyResult objects
    """
    #from time import time
    #from django.db import connection

    #start = time()
    #nstart = len(connection.queries)
    result_set = result_set_from_query_dict(request.data)
    #print '-->', len(connection.queries) - nstart, time() - start
    d = SocietyResultSetSerializer(result_set).data
    #print '==>', len(connection.queries) - nstart, time() - start
    #for q in connection.queries[-10:]:
    #    print q['sql'][:1000]
    return Response(d)


@api_view(['GET'])
@permission_classes((AllowAny,))
def get_categories(request):
    """
    Filters categories for sources, as some categories are empty for some sources
    """
    query_string = request.query_params['query']
    query_dict = json.loads(query_string)
    categories = VariableCategory.objects.all()
    source_categories = []
    if 'source' in query_dict:
        source = Source.objects.filter(id=query_dict['source'])
        variables = VariableDescription.objects.filter(source=source)
        for c in categories:
            if variables.filter(index_categories=c.id):
                source_categories.append(c)     
        return Response(VariableCategorySerializer(source_categories, many=True).data)
    else:
        return Response(VariableCategorySerializer(categories, many=True).data)


@api_view(['GET'])
@permission_classes((AllowAny,))
def get_dataset_sources(request):
    return Response(
        SourceSerializer(Source.objects.all().exclude(name=""), many=True).data)


class GeographicRegionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = GeographicRegionSerializer
    model = GeographicRegion
    filter_class = GeographicRegionFilter
    queryset = GeographicRegion.objects.all()

    
@api_view(['GET'])
@permission_classes((AllowAny,))
@renderer_classes((JSONRenderer,))
def get_min_and_max(request):
    query_string = request.query_params['query']
    query_dict = json.loads(query_string)
    if 'environmental_id' in query_dict:
        values = EnvironmentalValue.objects.filter(
            variable__id=query_dict['environmental_id'])
        min_value = 0
        max_value = 0
        for v in values:
            if v.value < min_value:
                min_value = v.value
            elif v.value > max_value:
                max_value = v.value
    else:
        min_value = None
        max_value = None
    return Response({'min': format(min_value, '.4f'), 'max': format(max_value, '.4f')})


@api_view(['GET'])
@permission_classes((AllowAny,))
@renderer_classes((JSONRenderer,))
def bin_cont_data(request):  # MAKE THIS GENERIC
    query_string = request.query_params['query']
    query_dict = json.loads(query_string)
    if 'bf_id' in query_dict:
        bf_variable = VariableDescription.objects.filter(id=query_dict['bf_id'])
        values = VariableCodedValue.objects.filter(variable__id=query_dict['bf_id'])
        min_value = None
        max_value = 0.0
        missing_data_option = False
        bins = []        
        for v in values:
            if re.search('[a-zA-Z]', v.coded_value):
                if not missing_data_option:
                    bins.append({
                        'code': v.coded_value,
                        'description': v.code.description,
                        'variable': query_dict['bf_id'],
                    })
                    missing_data_option = True
                continue
            else:
                v.coded_value = v.coded_value.replace(',', '')
                if min_value is None:
                    min_value = float(v.coded_value)
                elif float(v.coded_value) < min_value:
                    min_value = float(v.coded_value)
                elif float(v.coded_value) > max_value:
                    max_value = float(v.coded_value)
        
        data_range = max_value - min_value
        bin_size = data_range / 5
        min_bin = min_value
        for x in range(0, 5):
            min = min_bin
            max = min_bin + bin_size
            bins.append({
                'code': x,
                'description': str(min) + ' - ' + str(max),
                'min': min_bin,
                'max': min_bin + bin_size,
                'variable': query_dict['bf_id'],
            })
            min_bin = min_bin + bin_size + 1
    else:
        min_value = None
        max_value = None
    return Response(bins)


def newick_tree(key):
    # Get a newick format tree from a language tree id
    language_tree_id = key
    try:
        language_tree = LanguageTree.objects.get(pk=language_tree_id)
    except ObjectDoesNotExist:
        raise Http404
    n = NexusReader(language_tree.file.path)
    # Remove '[&R]' from newick string
    tree = re.sub(r'\[.*?\]', '', n.trees.trees[0])
    # Remove data before the =
    try:
        tree = tree[tree.index('=')+1:]
    except ValueError:
        tree = tree
    return tree


@api_view(['POST'])
@permission_classes((AllowAny,))
@renderer_classes((DPLACECsvRenderer,))
def csv_download(request):
    import datetime
    result_set = result_set_from_query_dict(request.data)
    response = Response(SocietyResultSetSerializer(result_set).data)
    filename = "dplace-societies-%s.csv" % datetime.datetime.now().strftime("%Y-%m-%d")
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename
    return response


@api_view(['POST'])
@permission_classes((AllowAny,))
@renderer_classes((ZipRenderer,))
def zip_legends(request):
    import datetime
    # query_string = request.QUERY_PARAMS['query']
    result_set = request.data  # json.loads(query_string)
    to_download = ZipResultSet()
    if 'name' in result_set:
        to_download.name = str(result_set['name'])
    if 'tree' in result_set:
        to_download.add_tree(str(result_set['tree']))
    if 'legends' in result_set:
        for l in result_set['legends']:
            legend = Legend(l['name'], l['svg'])
            to_download.legends.append(legend)
    response = Response(ZipResultSetSerializer(to_download).data)
    filename = "dplace-trees-%s.zip" % datetime.datetime.now().strftime("%Y-%m-%d")
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename
    return response
