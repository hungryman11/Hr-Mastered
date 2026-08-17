import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getLeaveTypes, LeaveType } from '../api/leaveTypes';
import { createLeaveRequest } from '../api/leaves';
import { useToast } from '../contexts/ToastContext';
import styles from './LeaveForm.module.css';
import { differenceInBusinessDays } from 'date-fns';

const LeaveForm = () => {
  const [step, setStep] = useState(1);
  const [leaveTypes, setLeaveTypes] = useState<LeaveType[]>([]);
  const { addToast } = useToast();
  const navigate = useNavigate();

  // Form State
  const [leaveType, setLeaveType] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [daysRequested, setDaysRequested] = useState('');
  const [reason, setReason] = useState('');
  const [contactDuringLeave, setContactDuringLeave] = useState('');
  const [emergencyContact, setEmergencyContact] = useState('');
  const [handoverContact, setHandoverContact] = useState('');
  const [document, setDocument] = useState<File | null>(null);

  useEffect(() => {
    getLeaveTypes().then(setLeaveTypes);
  }, []);

  useEffect(() => {
    if (startDate && endDate) {
      const days = differenceInBusinessDays(new Date(endDate), new Date(startDate)) + 1;
      setDaysRequested(days > 0 ? days.toString() : '0');
    }
  }, [startDate, endDate]);

  const selectedType = leaveTypes.find(t => t.uuid === leaveType);

  const handleNext = () => setStep(s => s + 1);
  const handlePrev = () => setStep(s => s - 1);

  const handleSubmit = async () => {
    try {
      const formData = new FormData();
      formData.append('leave_type', leaveType);
      formData.append('start_date', startDate);
      formData.append('end_date', endDate);
      formData.append('days_requested', daysRequested);
      formData.append('reason', reason);
      formData.append('contact_during_leave', contactDuringLeave);
      formData.append('emergency_contact', emergencyContact);
      formData.append('handover_contact', handoverContact);
      if (document) formData.append('document', document);

      const res = await createLeaveRequest(formData);
      addToast('Leave request submitted', 'success');
      navigate(`/app/leave/${res.uuid}`);
    } catch (err) {
      addToast('Failed to submit leave request', 'error');
    }
  };

  return (
    <div className={`card ${styles.wizardCard}`}>
      <h2 className={styles.title}>Request Leave</h2>
      
      <div className={styles.progress}>
        <div className={`${styles.step} ${step >= 1 ? styles.active : ''}`}>1. Details</div>
        <div className={`${styles.step} ${step >= 2 ? styles.active : ''}`}>2. Contact</div>
        <div className={`${styles.step} ${step >= 3 ? styles.active : ''}`}>3. Confirm</div>
      </div>

      <div className={styles.formContent}>
        {step === 1 && (
          <div className={styles.stepContent}>
            <label>
              Leave Type
              <select className="input-field" value={leaveType} onChange={e => setLeaveType(e.target.value)}>
                <option value="">Select a leave type</option>
                {leaveTypes.map(t => <option key={t.uuid} value={t.uuid}>{t.name}</option>)}
              </select>
            </label>
            <div className={styles.row}>
              <label>
                Start Date
                <input type="date" className="input-field" value={startDate} onChange={e => setStartDate(e.target.value)} />
              </label>
              <label>
                End Date
                <input type="date" className="input-field" value={endDate} onChange={e => setEndDate(e.target.value)} />
              </label>
            </div>
            <label>
              Days Requested
              <input type="number" className="input-field" value={daysRequested} onChange={e => setDaysRequested(e.target.value)} />
            </label>
            <label>
              Reason
              <textarea className="input-field" rows={4} value={reason} onChange={e => setReason(e.target.value)} required />
            </label>
          </div>
        )}

        {step === 2 && (
          <div className={styles.stepContent}>
            <label>
              Contact during leave
              <input type="text" className="input-field" value={contactDuringLeave} onChange={e => setContactDuringLeave(e.target.value)} />
            </label>
            <label>
              Emergency Contact Name & Phone
              <input type="text" className="input-field" value={emergencyContact} onChange={e => setEmergencyContact(e.target.value)} />
            </label>
            <label>
              Handover Contact & Notes
              <textarea className="input-field" rows={4} value={handoverContact} onChange={e => setHandoverContact(e.target.value)} />
            </label>
          </div>
        )}

        {step === 3 && (
          <div className={styles.stepContent}>
            <div className={styles.uploadArea}>
              <p>Supporting Document {selectedType?.requires_supporting_document ? <span className={styles.badgeReq}>Required</span> : <span className={styles.badgeOpt}>Optional</span>}</p>
              <input type="file" onChange={e => setDocument(e.target.files?.[0] || null)} />
            </div>
            <div className={styles.summary}>
              <h3>Summary</h3>
              <p><strong>Type:</strong> {selectedType?.name}</p>
              <p><strong>Dates:</strong> {startDate} to {endDate} ({daysRequested} days)</p>
              <p><strong>Reason:</strong> {reason}</p>
            </div>
          </div>
        )}
      </div>

      <div className={styles.actions}>
        {step > 1 && <button className="btn-secondary" onClick={handlePrev}>Back</button>}
        {step < 3 ? (
          <button className="btn-primary" onClick={handleNext} disabled={step === 1 && (!leaveType || !startDate || !endDate || !reason)}>Next</button>
        ) : (
          <button className="btn-primary" onClick={handleSubmit}>Submit Request</button>
        )}
      </div>
    </div>
  );
};

export default LeaveForm;
