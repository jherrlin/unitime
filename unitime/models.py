import requests
import re

from django.db import models


class TimeStampedModel(models.Model):
    """Gives the model created and modified timestamps"""
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        get_latest_by = 'modified'
        ordering = ('-modified', '-created')


class CourseCode(TimeStampedModel):
    course_code = models.CharField(max_length=6, unique=True)


class Course(TimeStampedModel):
    code = models.CharField(max_length=6)
    name = models.CharField(max_length=254, db_index=True)
    speed = models.CharField(max_length=20)
    points = models.CharField(max_length=20)
    syllabus = models.CharField(max_length=254)

    class Meta:
        unique_together = (("code", "name", "speed", "points"),)


class CourseOffering(TimeStampedModel):
    offering_id = models.CharField(max_length=254)
    registration_id = models.CharField(max_length=254)
    year = models.CharField(max_length=254)
    semester = models.CharField(max_length=254)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    class Meta:
        unique_together = (("offering_id", "registration_id", "year", "semester"),)

    @staticmethod
    def update_remote(course):
        url = f"""https://se.timeedit.net/web/lnu/db1/schema2/objects.txt
                  ?max=15&fr=t&partajax=t&im=f&sid=6&l=en_US&
                  search_text={course.code}&types=5"""
        try:
            req = requests.get(url, timeout=10)
            if req.status_code is 200:
                data = req.json()
                if data.get('count', 0) is not 0:  # There are more than one course offering
                    for course_id in data['ids']:
                        print(course_id)
                        url = f'https://se.timeedit.net/web/lnu/db1/schema2/objects/{course_id}/o.json'
                        req = requests.get(url, timeout=10)
                        if req.status_code is 200:
                            data = req.json()
                            data = data['records'][0]['fields']
                            CourseOffering.objects.update_or_create(
                                offering_id = course_id,
                                registration_id = data[6]['values'][0].split('-')[1],
                                defaults = {
                                    'offering_id': course_id,                                   # 0, id
                                    'registration_id': data[6]['values'][0].split('-')[1],      # 1, registration_id
                                    'year': data[6]['values'][0].split('-')[0][2:],             # 2, year, 18
                                    'semester': data[6]['values'][0].split('-')[0][:2],         # 3, semester, HT
                                    'course': course
                                })

        except Exception as e:
            print(e)


class Room(TimeStampedModel):
    name = models.CharField(max_length=254, unique=True)
    floor = models.IntegerField(blank=True, null=True)
    lat = models.FloatField(blank=True, null=True)
    lon = models.FloatField(blank=True, null=True)


class Lecture(TimeStampedModel):
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    teacher = models.CharField(max_length=254)
    info = models.CharField(max_length=254, blank=True)
    description = models.CharField(max_length=254, blank=True)
    room = models.ForeignKey(Room, null=True, on_delete=models.SET_NULL)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    course_offering = models.ForeignKey(CourseOffering, on_delete=models.CASCADE)

    class Meta:
        unique_together = (("start_datetime", "end_datetime", "teacher", "course"),)

    @staticmethod
    def update_remote(course):
        print('Lecture updates.')

        def _parse_room(room):
            match = re.search('[A-Z]+\d+[A-Z]+', room, re.IGNORECASE)
            if match:
                m = match.group()
                m = re.sub(r'_V$|_K$|V$|K$', '', m, flags=re.IGNORECASE)
                m = re.sub(r'A$|$B', '', m, flags=re.IGNORECASE)
                return m.upper()

        for co in CourseOffering.objects.filter(course=course):
            url = f"""https://se.timeedit.net/web/lnu/db1/schema2/s.json?object=courseevt_{co.semester}{co.year}-{co.registration_id}&tab=3"""
            try:
                req = requests.get(url, timeout=10)
                if req.status_code is 200:
                    data = req.json()
                    if data['info']['reservationcount'] > 0:
                        for event in data['reservations']:
                            try:
                                room_name = _parse_room(event['columns'][2])
                                if room_name:
                                    room, created = Room.objects.get_or_create(name=room_name)
                                obj, created = Lecture.objects.update_or_create(
                                    start_datetime = event['startdate'] + ' ' + event['starttime'],  # start_datetime
                                    end_datetime = event['startdate'] + ' ' + event['endtime'],    # endtime
                                    teacher = event['columns'][3],                            # teacher
                                    course = course,
                                    course_offering = co,
                                    defaults = {
                                        'start_datetime': event['startdate'] + ' ' + event['starttime'],  # start_datetime
                                        'end_datetime': event['startdate'] + ' ' + event['endtime'],      # end_datetime
                                        'teacher': event['columns'][3],                                   # teacher
                                        'room': room,
                                        'info': event['columns'][5],                                      # info
                                        'description': event['columns'][8],                               # desc
                                        'course': course,
                                        'course_offering': co
                                    })
                            except Exception as e:
                                print(e)
            except Exception as e:
                print(e)