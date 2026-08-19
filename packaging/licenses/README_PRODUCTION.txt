GPHI-TTS OPEN-SOURCE RELEASE CHECK
=================================

Purpose
-------
This directory is designed to be copied to packaging/licenses in the GPHI-TTS
repository. packaging/vntts.spec already copies that directory into the final
PyInstaller distribution.

Required release steps
----------------------
1. Create a clean Python 3.11 production virtual environment.
2. Install requirements/production.lock exactly.
3. Run:
       python scripts/export_production_licenses.py
4. Confirm packaging/licenses/components contains license/copyright files for
   the exact installed wheels.
5. Resolve LGPL source availability:
   - Qt/PySide6/Qt 6
   - lameenc/LAME
   - python-soxr/libsoxr (if bundled)
   - libsndfile from SoundFile wheels (if bundled)
   Replace LGPL_SOURCE_OFFER_TEMPLATE.txt placeholders OR ship corresponding
   source archives.
6. Build with the existing ONEDIR PyInstaller spec. Keep LGPL DLL/PYD/shared
   libraries separate and practically replaceable. Do not convert the release
   to a static/monolithic linkage without a new license review.
7. Verify only LGPL-eligible Qt modules are used. Do not add GPL-only Qt modules
   to a proprietary distribution without accepting GPL obligations or obtaining
   an appropriate commercial Qt license.
8. Keep THIRD_PARTY_NOTICES.txt and all generated component licenses in the
   shipped product.
9. Add the application's own commercial EULA/license separately. Third-party
   licenses do not license your proprietary application code.

UI note
-------
This pack does not require publishing the application's source code or placing
GitHub/source URLs on the main application screen. The shipped license/notices
must remain readily available to the recipient. Qt's LGPL guidance calls for a
prominent notice that an LGPL library is used; a release owner should ensure the
chosen presentation satisfies that requirement for the distribution channel.

Release gate
------------
Do not release if export_production_licenses.py reports a missing critical
package or if LGPL_SOURCE_OFFER_TEMPLATE.txt still contains placeholders.
