import { useState, useEffect, useRef } from "react";
import api from "./services/api";
import { uploadFileToBlob } from "./services/blob";
import { subscribeJobUpdate } from "./services/signalr";

const STATUS_ORDER = {
  CREATED: 0,
  UPLOADED: 1,
  QUEUED: 2,
  PROCESSING: 3,
  PROCESSED: 4,
  ERROR: 5,
};

function App() {
  const [file, setFile] = useState(null);
  const [jobId, setJobId] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [tags, setTags] = useState([]);

  const jobIdRef = useRef("");
  const seenStatusesRef = useRef(new Set());

  useEffect(() => {
    jobIdRef.current = jobId;
  }, [jobId]);

  useEffect(() => {
    const onJobUpdate = (data) => {
      if (data.documentId !== jobIdRef.current) return;

      const dedupeKey = `${data.documentId}:${data.status}`;
      if (seenStatusesRef.current.has(dedupeKey)) return;
      seenStatusesRef.current.add(dedupeKey);

      console.log("🔔 SignalR jobUpdate:", data);

      setStatus((prev) => {
        const prevRank = STATUS_ORDER[prev] ?? -1;
        const nextRank = STATUS_ORDER[data.status] ?? -1;
        if (nextRank < prevRank && data.status !== "ERROR") return prev;
        return data.status;
      });
      if (data.message) setMessage(data.message);
      if (data.tags?.length) setTags(data.tags);
    };

    const unsubscribe = subscribeJobUpdate(onJobUpdate);
    console.log("✅ Abonné aux mises à jour SignalR");

    return unsubscribe;
  }, []);

  const handleInitAndUpload = async () => {
    if (!file) {
      setMessage("Veuillez sélectionner un fichier.");
      return;
    }

    try {
      setLoading(true);
      setMessage("");

      const initResponse = await api.post("/jobs", {
        fileName: file.name,
        contentType: file.type || "application/octet-stream",
      });

      const { jobId, uploadUrl, status } = initResponse.data;

      seenStatusesRef.current = new Set();
      setJobId(jobId);
      setStatus(status);
      setTags([]);

      await uploadFileToBlob(uploadUrl, file);

      setMessage("Fichier uploadé avec succès.");
    } catch (error) {
      console.error(error);
      setMessage("Erreur pendant l'initialisation ou l'upload.");
    } finally {
      setLoading(false);
    }
  };

  const checkJobStatus = async () => {
    if (!jobId) return;

    try {
      const response = await api.get(`/jobs/${jobId}`);
      setStatus(response.data.status);
    } catch (error) {
      console.error(error);
      setMessage("Impossible de récupérer le statut du job.");
    }
  };

  return (
    <div style={{ maxWidth: 700, margin: "40px auto", fontFamily: "Arial, sans-serif" }}>
      <h1>Cloud Document Processing</h1>

      <input
        type="file"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />

      <div style={{ marginTop: 16 }}>
        <button onClick={handleInitAndUpload} disabled={loading}>
          {loading ? "Chargement..." : "Initialiser et uploader"}
        </button>
      </div>

      {jobId && (
        <div style={{ marginTop: 24, padding: 16, background: "#f5f5f5", borderRadius: 8 }}>
          <p><strong>Job ID :</strong> {jobId}</p>
          <p>
            <strong>Status :</strong>{" "}
            <span style={{ color: status === "ERROR" ? "red" : status === "PROCESSED" ? "green" : "blue" }}>
              {status}
            </span>
          </p>
          {tags.length > 0 && (
            <p><strong>Tags générés :</strong> {tags.map(t => <span key={t} style={{marginRight: 8, background:"#ddd", padding:"2px 6px", borderRadius:4}}>{t}</span>)}</p>
          )}
          <button onClick={checkJobStatus} style={{ marginTop: 12 }}>Vérifier le statut manuellement</button>
        </div>
      )}

      {message && (
        <div style={{ marginTop: 24 }}>
          <p>{message}</p>
        </div>
      )}
    </div>
  );
}

export default App;