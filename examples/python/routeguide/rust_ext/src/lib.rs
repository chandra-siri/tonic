use pyo3::prelude::*;
use pyo3::types::PyBytes;
use std::sync::Arc;
use tokio::sync::Mutex;
use tonic::Request;
use prost::Message;

pub mod routeguide {
    tonic::include_proto!("routeguide");
}

use routeguide::route_guide_client::RouteGuideClient;
use routeguide::{Rectangle, BytesContainer};


#[pyclass]
struct FeatureStream {
    stream: Arc<Mutex<tonic::Streaming<BytesContainer>>>,
}

#[pymethods]
impl FeatureStream {
    fn __aiter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __anext__<'py>(&self, py: Python<'py>) -> PyResult<Option<&'py PyAny>> {
        let stream_arc = self.stream.clone();
        
        let py_future = pyo3_asyncio::tokio::future_into_py(py, async move {
            let mut stream = stream_arc.lock().await;

            // Wait for the next message asynchronously
            match stream.message().await {
                Ok(Some(container)) => {
                    // Encode the full protobuf into bytes to send seamlessly to Python
                    let mut buf = Vec::new();
                    container.encode(&mut buf)
                        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Encode error: {}", e)))?;
                    
                    Python::with_gil(|py| -> PyResult<PyObject> {
                        // Return the serialized protobuf as native Python bytes
                        Ok(PyBytes::new(py, &buf).into())
                    })
                }
                Ok(None) => {
                    // Signal the end of the async iterator back up into Python's loop
                    Err(pyo3::exceptions::PyStopAsyncIteration::new_err(""))
                }
                Err(e) => {
                    // Transport or gRPC crash bubble
                    Err(pyo3::exceptions::PyRuntimeError::new_err(format!("Stream error: {}", e)))
                }
            }
        })?;

        Ok(Some(py_future))
    }
}


#[pyclass]
struct RustRouteGuideStub {
    client: RouteGuideClient<tonic::transport::Channel>,
}

#[pymethods]
impl RustRouteGuideStub {
    #[staticmethod]
    fn connect<'py>(py: Python<'py>, target: String) -> PyResult<&'py PyAny> {
        pyo3_asyncio::tokio::future_into_py(py, async move {
            let client = RouteGuideClient::connect(target).await
                .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Connect error: {}", e)))?;
            Ok(RustRouteGuideStub { client })
        })
    }

    fn list_features<'py>(&self, py: Python<'py>, payload_bytes: &[u8]) -> PyResult<&'py PyAny> {
        // Decode the Python-provided binary payload into the internal Rust Protobuf via Prost
        let rectangle = Rectangle::decode(payload_bytes)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Decode protobuf error: {}", e)))?;

        // Client must be cloned because it borrows heavily and is moving into the inner block
        let mut client = self.client.clone();

        pyo3_asyncio::tokio::future_into_py(py, async move {
            let stream = client.list_features(Request::new(rectangle)).await
                .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("RPC error: {}", e)))?
                .into_inner();
            
            Ok(FeatureStream {
                stream: Arc::new(Mutex::new(stream)),
            })
        })
    }
}


#[pymodule]
fn routeguide_rust_client(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<RustRouteGuideStub>()?;
    Ok(())
}
