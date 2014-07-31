/**
 * Controller for the search tab. pops in sub controllers for geographic/cultural/etc
 *
 * @param $scope
 * @param colorMapService
 * @param searchModelService
 * @param FindSocieties
 * @constructor
 */
function SearchCtrl($scope, colorMapService, searchModelService, FindSocieties) {
    $scope.setActive('search');
    $scope.searchModel = searchModelService.getModel();
    $scope.selectedButton = $scope.searchModel.selectedButton;
    $scope.buttons = [
        {value:'geographic', name:'Geographic', badgeValue:
            function() { return $scope.searchModel.getGeographicRegions().badgeValue; }
        },
        {value:'cultural', name:'Cultural Traits', badgeValue:
            function() { return $scope.searchModel.getCulturalTraits().badgeValue; }
        },
        {value:'environmental', name:'Environmental', badgeValue:
            function() { return $scope.searchModel.getEnvironmentalData().badgeValue; }
        },
        {value:'language', name:'Language', badgeValue:
            function() { return $scope.searchModel.getLanguageClassifications().badgeValue; }
        }
    ];

    $scope.buttonChanged = function(selectedButton) {
        $scope.selectedButton = selectedButton;
    };

    // All of this needs to move into model
    $scope.disableSearchButton = function () {
        $scope.searchButton.disabled = true;
        $scope.searchButton.text = 'Working...';
    };

    $scope.enableSearchButton = function () {
        $scope.searchButton.disabled = false;
        $scope.searchButton.text = 'Search';
    };

    $scope.assignColors = function() {
        var colorMap = colorMapService.generateColorMap($scope.getSocietyIds());
        $scope.searchModel.getSocieties().forEach(function(container) {
            container.society.style = {'background-color' : colorMap[container.society.id] };
        });
    };

    // This method merges the current searchQuery object with the incoming searchQuery
    $scope.updateSearchQuery = function(searchQuery) {
        for(var propertyName in searchQuery) {
            $scope.searchModel.query[propertyName] = searchQuery[propertyName];
        }
    };

    var searchCompletedCallback = function() {
        $scope.enableSearchButton();
        $scope.assignColors();
        $scope.switchToResults();
    };

    $scope.searchSocieties = function() {
        $scope.disableSearchButton();
        var query = $scope.searchModel.query;
        $scope.searchModel.results = FindSocieties.find(query, searchCompletedCallback);
    };

    // resets this object state and the search query.
    $scope.resetSearch = function() {
        $scope.searchModel.reset();
        // send a notification so that the individual controllers reload their state
        $scope.$broadcast('searchModelReset');
    };

}