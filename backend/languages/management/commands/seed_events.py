"""
Seed historical event annotations for the timeline.

Usage:
  python manage.py seed_events
"""
import datetime

from django.core.management.base import BaseCommand

from languages.models import HistoricalEvent, Language

EVENTS = [
    {
        'date': datetime.date(2012, 3, 1),
        'title': 'Go 1.0 released',
        'language': 'Go',
        'impact': (
            'Google releases Go 1.0 with a stability guarantee. Systems and cloud '
            'infrastructure adoption begins, driven by concurrency primitives and fast '
            'compile times.'
        ),
    },
    {
        'date': datetime.date(2012, 10, 1),
        'title': 'TypeScript 1.0 public preview',
        'language': 'TypeScript',
        'impact': (
            'Microsoft unveils TypeScript as a typed superset of JavaScript. '
            'Adoption is slow initially but accelerates dramatically once Angular 2 '
            'mandates it in 2016.'
        ),
    },
    {
        'date': datetime.date(2013, 12, 1),
        'title': 'Rust 0.9 — memory safety without GC proven viable',
        'language': 'Rust',
        'impact': (
            'Rust reaches its pre-1.0 milestone demonstrating ownership and borrow '
            'checker in real projects. Mozilla begins replacing C++ subsystems in Firefox.'
        ),
    },
    {
        'date': datetime.date(2014, 9, 1),
        'title': 'Swift 1.0 — Apple replaces Objective-C',
        'language': 'Swift',
        'impact': (
            'Apple releases Swift at WWDC 2014 and open-sources it by year-end. '
            'Objective-C job postings begin a multi-year decline as iOS developers migrate.'
        ),
    },
    {
        'date': datetime.date(2015, 1, 1),
        'title': 'Python 3 adoption inflection point',
        'language': 'Python',
        'impact': (
            'SO Developer Survey 2015 marks the first year Python 3 downloads exceed '
            'Python 2. Scientific computing libraries (NumPy, SciPy, pandas) complete '
            'their Python 3 ports.'
        ),
    },
    {
        'date': datetime.date(2015, 5, 1),
        'title': 'Rust 1.0 stable — systems language with memory safety',
        'language': 'Rust',
        'impact': (
            'Rust 1.0 ships with a stable API surface. The ownership model is proven '
            'production-ready. Rust wins "Most Loved Language" in the SO survey for the '
            'first time — a streak that continues for seven consecutive years.'
        ),
    },
    {
        'date': datetime.date(2015, 8, 1),
        'title': 'Go 1.5 — concurrent GC eliminates stop-the-world pauses',
        'language': 'Go',
        'impact': (
            'Go 1.5 ships a fully concurrent garbage collector, dropping worst-case GC '
            'latency from hundreds of milliseconds to sub-millisecond. Cloud adoption '
            'accelerates; Docker and Kubernetes are both written in Go.'
        ),
    },
    {
        'date': datetime.date(2016, 2, 1),
        'title': 'Kotlin 1.0 stable on JVM',
        'language': 'Kotlin',
        'impact': (
            'JetBrains ships Kotlin 1.0 with a backwards-compatibility pledge. '
            'The language offers null-safety and concise syntax while compiling to '
            'standard JVM bytecode, positioning it as a pragmatic Java replacement.'
        ),
    },
    {
        'date': datetime.date(2016, 4, 1),
        'title': 'Rust: first "Most Loved" SO survey win',
        'language': 'Rust',
        'impact': (
            'Rust tops the Stack Overflow Developer Survey "Most Loved Language" '
            'category for the first time. This begins an unprecedented seven-year '
            'streak, cementing community sentiment as a leading health indicator.'
        ),
    },
    {
        'date': datetime.date(2017, 5, 1),
        'title': 'Kotlin becomes official Android language',
        'language': 'Kotlin',
        'impact': (
            'Google announces first-class Kotlin support for Android at Google I/O 2017. '
            'Kotlin job postings double within six months; Java Android postings plateau.'
        ),
    },
    {
        'date': datetime.date(2018, 1, 1),
        'title': 'Python AI/ML surge — TensorFlow & PyTorch mainstream',
        'language': 'Python',
        'impact': (
            'TensorFlow 1.4 and PyTorch 0.4 both achieve production-ready status. '
            'Python becomes the de-facto language of machine learning research and '
            'production, driving a GitHub activity spike that shows clearly in the data.'
        ),
    },
    {
        'date': datetime.date(2018, 8, 1),
        'title': 'Julia 1.0 — scientific computing challenger',
        'language': 'Julia',
        'impact': (
            'Julia 1.0 ships with a stability commitment. Promises Python-like '
            'ergonomics with near-C performance via JIT compilation. Academic adoption '
            'accelerates in computational biology and quantitative finance.'
        ),
    },
    {
        'date': datetime.date(2019, 11, 1),
        'title': 'TypeScript surpasses Ruby and Go in GitHub usage',
        'language': 'TypeScript',
        'impact': (
            'GitHub\'s Octoverse 2019 report places TypeScript as the 7th most-used '
            'language by repository, overtaking both Ruby and Go. Angular, React, and '
            'Vue all adopt TypeScript as their preferred authoring language.'
        ),
    },
    {
        'date': datetime.date(2022, 11, 1),
        'title': 'ChatGPT launches — LLM-era Python explosion',
        'language': 'Python',
        'impact': (
            'OpenAI releases ChatGPT; the LLM developer ecosystem is almost entirely '
            'Python-first (LangChain, Hugging Face, OpenAI SDK). Python GitHub activity '
            'and SO questions hit all-time highs. The gap between Python and every other '
            'language widens dramatically.'
        ),
    },
]


class Command(BaseCommand):
    help = 'Seed historical event annotations for the timeline'

    def handle(self, *args, **options):
        lang_map = {lang.name: lang for lang in Language.objects.all()}
        created = 0
        skipped = 0

        for evt in EVENTS:
            lang = lang_map.get(evt['language'])
            obj, was_created = HistoricalEvent.objects.update_or_create(
                title=evt['title'],
                defaults={
                    'date': evt['date'],
                    'language': lang,
                    'impact_description': evt['impact'],
                },
            )
            if was_created:
                created += 1
            else:
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'seed_events: {created} created, {skipped} updated'
            )
        )
