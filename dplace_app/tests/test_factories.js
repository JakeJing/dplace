describe('Testing factories', function() {
    var mockLangFamilyFactory, $httpBackend, results;
    beforeEach(module('dplaceServices'));
    beforeEach(function() {
        inject(function($injector) {
            $httpBackend = $injector.get('$httpBackend');
            mockLangFamilyFactory = $injector.get('LanguageFamily');
        });
    });
    
    describe('language families', function() {
        it('should get language families', inject(function(LanguageFamily) {
            results = {
                "count": 2,
                "results": [
                {
                    "id": 77,
                    "scheme": "G",
                    "name": "Abkhaz-Adyge",
                    "language_count": 2
                },
                {
                    "id": 7,
                    "scheme": "G",
                    "name": "Afro-Asiatic",
                    "language_count": 91
                },
                ]
            };
            $httpBackend.whenGET('/api/v1/language_families?page_size=1000')
                .respond(JSON.stringify(results));
            response = mockLangFamilyFactory.query();
            $httpBackend.flush();
            expect(response.length).toEqual(2);
            expect(response[0].id).toEqual(77);
            expect(response[1].id).toEqual(7);
            expect(response[0].name).toEqual("Abkhaz-Adyge");
            expect(response[1].name).toEqual("Afro-Asiatic");
        }));
    });
});