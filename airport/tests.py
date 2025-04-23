from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from airport.models import Airport, Route, AirplaneType, Airplane, Crew, Flight
from airport.serializers import AirportSerializer

AIRPORT_URL = reverse("airport:airport-list")
ROUTE_URL = reverse("airport:route-list")
FLIGHT_URL = reverse("airport:flight-list")


def sample_airport(**params):
    defaults = {
        "name": "Sample Airport",
        "closest_big_city": "Sample Location",
    }
    defaults.update(params)
    return Airport.objects.create(**defaults)


class UnauthenticatedAirportApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required to access the airport API."""
        res = self.client.get(AIRPORT_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedAirportApiTests(TestCase):
    def setUp(self):
        """Create an authenticated user and set up API client."""
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com", "testpass"
        )
        self.client.force_authenticate(self.user)

    def test_list_airports(self):
        """Test that list of airports is returned correctly."""
        sample_airport()
        sample_airport()

        res = self.client.get(AIRPORT_URL)

        airports = Airport.objects.order_by("id")
        serializer = AirportSerializer(airports, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_airport_forbidden(self):
        """Test that a non-staff user cannot create an airport."""
        payload = {
            "name": "New Airport",
            "closest_big_city": "New Location",
        }
        res = self.client.post(AIRPORT_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminAirportApiTests(TestCase):
    def setUp(self):
        """Create an admin user and set up API client."""
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com", "testpass", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_airport(self):
        """Test that admin user can create an airport."""
        payload = {
            "name": "New Airport",
            "closest_big_city": "New Location",
        }
        res = self.client.post(AIRPORT_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        airport = Airport.objects.get(id=res.data["id"])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(airport, key))


class FlightImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com", "testpass",
        )
        self.client.force_authenticate(self.user)
        self.source_airport = Airport.objects.create(name="Source Airport")
        self.destination_airport = Airport.objects.create(name="Destination Airport")

        self.airplane_type = AirplaneType.objects.create(name="Boeing 747")
        self.airplane = Airplane.objects.create(name="Airplane 1", rows=10, seats_in_row=6,
                                                airplane_type=self.airplane_type)
        self.crew_member = Crew.objects.create(first_name="John", last_name="Doe")
        self.route = Route.objects.create(source=self.source_airport, destination=self.destination_airport,
                                          distance=500)
        self.flight = Flight.objects.create(
            route=self.route,
            airplane=self.airplane,
            departure_time=timezone.now(),
            arrival_time=timezone.now() + timezone.timedelta(hours=1)
        )
        self.flight.crew.add(self.crew_member)

    def test_image_url_is_shown_on_flight_detail(self):
        response = self.client.get(reverse("airport:flight-detail", args=[self.flight.id]))
        self.assertEqual(response.status_code, 200)

    def test_image_url_is_shown_on_flight_list(self):
        response = self.client.get(reverse("airport:flight-list"))
        self.assertEqual(response.status_code, 200)
        