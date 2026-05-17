import { useState, useEffect, useRef } from "react";
import * as signalR from "@microsoft/signalr";
import api from "./services/api";
import { uploadFileToBlob } from "./services/blob";

function App() {
  const [file, setFile] = useState(null);
  const [jobId, setJobId] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [tags, setTags] = useState([]);

  // Référence pour accéder à la valeur à jour de jobId dans la callback SignalR
  const jobIdRef = useRef("");
  useEffect(() => {
    jobIdRef.current = jobId;
  }, [jobId]);

  // Connexion SignalR au montage
  useEffect(() => {
    const connection = new signalR.HubConnectionBuilder()
      // URL de l'Azure Function locale qui expose /api/negotiate
      .withUrl("http://localhost:7071/api")
      .withAutomaticReconnect()
      .build();

    connection.on("jobUpdate", (data) => {
      console.log("🔔 SignalR jobUpdate:", data);
      // On ne met à jour l'UI que si l'event concerne le job en cours
      if (data.documentId === jobIdRef.current) {
        setStatus(data.status);
        if (data.message) setMessage(data.message);
        if (data.tags) setTags(data.tags);
      }
    });

    connection.start()
      .then(() => console.log("✅ Connecté à Azure SignalR"))
      .catch(err => console.error("❌ Erreur connexion SignalR:", err));

    return () => {
      connection.stop();
    };
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

      setJobId(jobId);
      setStatus(status);

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