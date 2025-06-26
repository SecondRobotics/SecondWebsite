import pytest

from django.urls import reverse


@pytest.mark.django_db
def test_home_view(client):
    url = reverse('home')
    response = client.get(url)
    assert response.status_code == 200
    # assert 'Welcome to the home' in response.content

# TODO: Add more tests for the dynamic views (such as the highscore or ranked views)
