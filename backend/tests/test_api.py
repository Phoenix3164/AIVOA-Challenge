from fastapi.testclient import TestClient
import fitz
from app.main import app


def test_health():
    with TestClient(app) as client:
        response = client.get('/api/health')
        assert response.status_code == 200
        assert response.json()['status'] == 'ok'


def test_copilot_create_and_rca():
    with TestClient(app) as client:
        created = client.post('/api/investigations', json={})
        assert created.status_code == 200
        investigation_id = created.json()['id']
        message = 'During manufacturing of Metformin Hydrochloride API batch MFH260712A, temperature exceeded approved range of 75-78 C and reached 82 C for 18 minutes during reaction stage. Batch was placed on hold.'
        copilot = client.post('/api/copilot/message', json={'investigation_id': investigation_id, 'message': message})
        assert copilot.status_code == 200
        assert copilot.json()['fields']['batch_number'] == 'MFH260712A'
        assert copilot.json()['risk_assessment']['level'] == 'High'
        rca = client.post(f'/api/investigations/{investigation_id}/analyze', json={'analysis_type': 'rca'})
        assert rca.status_code == 200
        assert len(rca.json()['root_causes']) == 1
        assert rca.json()['root_causes'][0]['confirmed'] is False


def test_pdf_upload_populates_persists_and_allows_human_edit():
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), """Product / API: Metformin Hydrochloride API
Batch number: MET26015
Manufacturing date: 15 November 2026
Department: Quality Control
Incident category: OOS Moisture Result
Reported result: Moisture content 1.8%
Approved specification limit: 0.5%
Affected quantity: 250 kg (demonstration scenario)
Batch disposition: Pending qualified QA assessment""", fontsize=10)
    payload = document.tobytes()
    with TestClient(app) as client:
        created = client.post('/api/investigations', json={})
        investigation_id = created.json()['id']
        uploaded = client.post('/api/copilot/upload', data={'investigation_id': str(investigation_id)}, files={'file': ('metformin.pdf', payload, 'application/pdf')})
        assert uploaded.status_code == 200
        assert uploaded.json()['investigation']['id'] == investigation_id
        assert uploaded.json()['investigation']['product_name'] == 'Metformin Hydrochloride API'
        assert uploaded.json()['investigation']['batch_number'] == 'MET26015'
        assert uploaded.json()['investigation']['department'] == 'Quality Control'
        assert uploaded.json()['investigation']['actual_parameters']['Moisture Content'] == '1.8%'
        assert uploaded.json()['investigation']['field_metadata']['batch_number']['requires_review'] is True
        assert uploaded.json()['investigation']['title'] == 'Metformin Hydrochloride API | MET26015 | OOS Moisture Result'
        assert len(uploaded.json()['capas']) >= 2
        assert len(uploaded.json()['investigation']['capa_actions']) >= 2
        assert uploaded.json()['investigation']['evidence_gaps']
        first_capa = uploaded.json()['investigation']['capa_actions'][0]
        capa_update = client.patch(f"/api/capa/{first_capa['id']}", json={'status': 'Draft', 'description': 'QA-reviewed provisional action'})
        assert capa_update.status_code == 200
        rerun = client.post(f'/api/investigations/{investigation_id}/analyze', json={'analysis_type': 'capa'})
        assert rerun.status_code == 200
        edited = client.patch(f'/api/investigations/{investigation_id}', json={'batch_number': 'QA-EDITED'})
        assert edited.status_code == 200
        restored = client.get(f'/api/investigations/{investigation_id}')
        assert restored.status_code == 200
        assert restored.json()['batch_number'] == 'QA-EDITED'
        assert restored.json()['field_metadata']['batch_number']['source'] == 'human'
        assert restored.json()['documents'][0]['filename'] == 'metformin.pdf'
        assert any(capa['description'] == 'QA-reviewed provisional action' and capa['status'] == 'Draft' for capa in restored.json()['capa_actions'])
        assert len(restored.json()['capa_actions']) == len(uploaded.json()['investigation']['capa_actions'])


def test_chat_message_does_not_repeat_document_extraction():
    with TestClient(app) as client:
        created = client.post('/api/investigations', json={})
        response = client.post('/api/copilot/message', json={'investigation_id': created.json()['id'], 'message': 'hi'})
        assert response.status_code == 200
        assert response.json()['intent'] == 'chat'
        assert response.json()['fields'] == {}


def test_report_pdf_uses_saved_investigation_data():
    with TestClient(app) as client:
        created = client.post('/api/investigations', json={})
        investigation_id = created.json()['id']
        client.patch(f'/api/investigations/{investigation_id}', json={
            'product_name': 'Metformin Hydrochloride API',
            'batch_number': 'MET26118',
            'incident_category': 'OOS Moisture Result',
            'deviation_description': 'Synthetic report verification.',
        })
        report = client.get(f'/api/investigations/{investigation_id}/report')
        assert report.status_code == 200
        assert report.headers['content-type'].startswith('application/pdf')
        assert report.content.startswith(b'%PDF')
        text = '\n'.join(page.get_text() for page in fitz.open(stream=report.content, filetype='pdf'))
        assert 'Metformin Hydrochloride API' in text
        assert 'MET26118' in text


def test_upload_rejects_missing_id_invalid_and_empty_pdfs():
    empty_document = fitz.open()
    empty_document.new_page()
    with TestClient(app) as client:
        invalid = client.post('/api/copilot/upload', data={'investigation_id': '1'}, files={'file': ('notes.txt', b'not a pdf', 'text/plain')})
        assert invalid.status_code == 400
        missing_id = client.post('/api/copilot/upload', files={'file': ('empty.pdf', empty_document.tobytes(), 'application/pdf')})
        assert missing_id.status_code == 422
        empty = client.post('/api/copilot/upload', data={'investigation_id': '1'}, files={'file': ('empty.pdf', empty_document.tobytes(), 'application/pdf')})
        assert empty.status_code == 400
