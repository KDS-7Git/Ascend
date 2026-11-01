// Portable source-mode probe: the pinned WebGoat JDK image has no curl binary.
import java.net.HttpURLConnection;
import java.net.URI;

class Health {
    public static void main(String[] args) throws Exception {
        HttpURLConnection connection = (HttpURLConnection)
            URI.create("http://127.0.0.1:8080/WebGoat/login").toURL().openConnection();
        connection.setConnectTimeout(2000);
        connection.setReadTimeout(2000);
        int status = connection.getResponseCode();
        connection.disconnect();
        System.exit(status == 200 ? 0 : 1);
    }
}
