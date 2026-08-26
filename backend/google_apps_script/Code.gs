/**
 * ApplyFlow Enterprise Google Drive Storage Web App (Production Ready)
 * Deploy as: Web App
 * Execute as: Me (your personal Google Account)
 * Who has access: Anyone (with the secret script URL)
 */

const ROOT_FOLDER_ID = "11N7TFi1dQ98L9TRgV87966JAliQ5jcIq";

function doPost(e) {
  try {
    const action = (e && e.parameter && e.parameter.action) || "upload";

    if (action === "upload") {
      return uploadFile(e);
    }

    if (action === "delete") {
      return deleteFile(e.parameter.fileId);
    }

    return ContentService.createTextOutput(
      JSON.stringify({ success: false, message: "Invalid POST action" })
    ).setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(
      JSON.stringify({ success: false, message: err.toString() })
    ).setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  try {
    const action = e && e.parameter && e.parameter.action;
    const fileId = e && e.parameter && e.parameter.fileId;

    switch (action) {
      case "download":
        return downloadFile(fileId);

      case "metadata":
        return getMetadata(fileId);

      case "delete":
        return deleteFile(fileId);

      default:
        return ContentService.createTextOutput(
          JSON.stringify({
            success: false,
            message: "Unknown action. Supported actions: download, metadata, delete."
          })
        ).setMimeType(ContentService.MimeType.JSON);
    }
  } catch (err) {
    return ContentService.createTextOutput(
      JSON.stringify({ success: false, message: err.toString() })
    ).setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Ingests resume file and stores inside Client-specific folder in Google Drive.
 */
function uploadFile(e) {
  try {
    let blob;
    let filename = (e.parameter && e.parameter.filename) || "candidate_resume.pdf";
    const clientName = (e.parameter && e.parameter.client) || "General";
    const rootFolderId = (e.parameter && e.parameter.rootFolderId) || ROOT_FOLDER_ID;

    // Handle Multipart form file or Base64 content
    if (e.files && e.files.file) {
      blob = e.files.file;
    } else if (e.parameter && e.parameter.content) {
      const decodedBytes = Utilities.base64Decode(e.parameter.content);
      blob = Utilities.newBlob(decodedBytes, "application/pdf", filename);
    } else if (e.postData && e.postData.contents) {
      try {
        const body = JSON.parse(e.postData.contents);
        if (body.content) {
          const decodedBytes = Utilities.base64Decode(body.content);
          blob = Utilities.newBlob(decodedBytes, "application/pdf", body.filename || filename);
        }
      } catch (parseErr) {}
    }

    if (!blob) {
      return ContentService.createTextOutput(
        JSON.stringify({ success: false, message: "No file content or base64 payload provided." })
      ).setMimeType(ContentService.MimeType.JSON);
    }

    const rootFolder = DriveApp.getFolderById(rootFolderId);
    let clientFolder;
    const folders = rootFolder.getFoldersByName(clientName);

    if (folders.hasNext()) {
      clientFolder = folders.next();
    } else {
      clientFolder = rootFolder.createFolder(clientName);
    }

    const file = clientFolder.createFile(blob);
    file.setName(filename);

    return ContentService.createTextOutput(
      JSON.stringify({
        success: true,
        fileId: file.getId(),
        fileName: file.getName(),
        mimeType: file.getMimeType(),
        url: file.getUrl()
      })
    ).setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(
      JSON.stringify({ success: false, message: err.toString() })
    ).setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Streams exact file bytes encoded in Base64 for secure proxying by FastAPI.
 */
function downloadFile(fileId) {
  try {
    if (!fileId) {
      return ContentService.createTextOutput(
        JSON.stringify({ success: false, message: "fileId parameter is required" })
      ).setMimeType(ContentService.MimeType.JSON);
    }

    const file = DriveApp.getFileById(fileId);
    const blob = file.getBlob();
    const bytes = blob.getBytes();
    const base64Content = Utilities.base64Encode(bytes);

    return ContentService.createTextOutput(
      JSON.stringify({
        success: true,
        fileId: file.getId(),
        fileName: file.getName(),
        mimeType: file.getMimeType(),
        size: file.getSize(),
        base64: base64Content
      })
    ).setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(
      JSON.stringify({ success: false, message: err.toString() })
    ).setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Returns metadata of a stored resume in Google Drive.
 */
function getMetadata(fileId) {
  try {
    if (!fileId) {
      return ContentService.createTextOutput(
        JSON.stringify({ success: false, message: "fileId is required" })
      ).setMimeType(ContentService.MimeType.JSON);
    }

    const file = DriveApp.getFileById(fileId);

    return ContentService.createTextOutput(
      JSON.stringify({
        success: true,
        fileName: file.getName(),
        mimeType: file.getMimeType(),
        size: file.getSize(),
        url: file.getUrl()
      })
    ).setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(
      JSON.stringify({ success: false, message: err.toString() })
    ).setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Moves file to Trash in personal Google Drive.
 */
function deleteFile(fileId) {
  try {
    if (!fileId) {
      return ContentService.createTextOutput(
        JSON.stringify({ success: false, message: "fileId is required" })
      ).setMimeType(ContentService.MimeType.JSON);
    }

    const file = DriveApp.getFileById(fileId);
    file.setTrashed(true);

    return ContentService.createTextOutput(
      JSON.stringify({ success: true, message: "File trashed successfully" })
    ).setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(
      JSON.stringify({ success: false, message: err.toString() })
    ).setMimeType(ContentService.MimeType.JSON);
  }
}
