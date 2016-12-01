package nist.oar.id;

/**
 * An exception indicating incorrect use of an identifier.
 */
public IDException extends Exception {

    /**
     * the ID that was misused
     */
    protected String id = null;

    /**
     * create the exception
     * @param msg   the message explaining the misuse
     */
    public IDException(String msg) {
        super(msg);
        this.id = id;
    }

    /**
     * create the exception
     * @param msg   the message explaining the misuse
     * @param id    the identifier that was misused
     */
    public IDException(String msg, String id) {
        super(msg);
        this.id = id;
    }
}
