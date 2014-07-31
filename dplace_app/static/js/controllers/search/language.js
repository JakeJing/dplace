function LanguageCtrl($scope, searchModelService, LanguageClass, LanguageClassification) {
    var linkModel = function() {
        // Get a reference to the language classifications from the model
        $scope.languageClassifications = searchModelService.getModel().getLanguageClassifications();
    };
    $scope.$on('searchModelReset', linkModel); // When model is reset, update our model
    linkModel();

    var levels = $scope.languageClassifications.levels;

    function levelToIndex(levelObject) {
        return levelObject.level - 1;
    }
    function indexToLevel(levelIndex) {
        return levels[levelIndex];
    }

    function selectedItemAtLevel(languageFilter,levelObject) {
        return languageFilter[levelToIndex(levelObject)].selectedItem;
    }

    function queryParameterForLevel(levelObject) {
        return 'class_' + levelObject.tag;
    }

    function updateClassifications(languageFilter) {
        var params = {};
        levels.forEach(function (levelObject) {
            var selectedItem = selectedItemAtLevel(languageFilter, levelObject);
            if(selectedItem) {
                var param = queryParameterForLevel(levelObject);
                params[param] = selectedItem.id;
            }
        });
        if(Object.keys(params).length == 0) {
            /* Nothing selected at any level */
            languageFilter.classifications = [];
        } else {
            languageFilter.classifications = LanguageClassification.query(params);
        }
    }

    function updateItems(languageFilter, parentObject, levelObject) {
        var index = levelToIndex(levelObject);
        languageFilter[index].items = LanguageClass.query({parent: parentObject.id, level: levelObject.level});
        languageFilter[index].selectedItem = undefined;
    }

    function clearItems(languageFilter, levelObject) {
        var index = levelToIndex(levelObject);
        languageFilter[index].items = [];
        languageFilter[index].selectedItem = undefined;
    }

    $scope.selectionChanged = function(languageFilter, levelObject) {
        var changedIndex = levelToIndex(levelObject);
        var parentObject = selectedItemAtLevel(languageFilter, levelObject);
        if(changedIndex + 1 < levels.length) {
            // Update the next level
            var childLevel = indexToLevel(changedIndex + 1)
            updateItems(languageFilter, parentObject, childLevel);
        }
        if(changedIndex + 2 < levels.length) {
            var childLevel = indexToLevel(changedIndex + 2)
            clearItems(languageFilter, childLevel);
        }
        updateClassifications(languageFilter);
    };

    function getSelectedLanguageClassifications(languageFilter) {
        return languageFilter.classifications.filter( function (classification) {
            return classification.isSelected;
        });
    }

    $scope.getLanguageQueryFilters = function() {
        var languageQueryFilters = [];
        $scope.languageClassifications.languageFilters.forEach(function(languageFilter) {
            var selectedClassifications = getSelectedLanguageClassifications(languageFilter);
            var languageIds = selectedClassifications.map(function (classification) { return classification.language.id; });
            languageQueryFilters.push({language_ids: languageIds});
        });
        return languageQueryFilters;
    };

    $scope.classificationSelectionChanged = function(classification) {
        // Since the selections are stored deep in the model, this is greatly simplified by +1 / -1
        // But if we add "select all", this will not work
        if(classification.isSelected) {
            $scope.languageClassifications.badgeValue++;
        } else {
            $scope.languageClassifications.badgeValue--;
        }
    };

    $scope.doSearch = function() {
        var filters = $scope.getLanguageQueryFilters();
        $scope.updateSearchQuery({ language_filters: filters });
        $scope.searchSocieties();
    };

}