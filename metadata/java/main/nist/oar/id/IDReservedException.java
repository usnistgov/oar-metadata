package nist.oar.id;

/**
 * An exception indicating an attempt to claim or register an ID that 
 * has already been claimed, registered, or otherwise reserved. 
 */
public IDReservedException extends IDException {

    /**
     * create the exception  
     * @param id    the identifier that was misused
     * @param msg   the message explaining the misuse
     */
    public IDReservedException(String id, String msg) {
        super(msg, id);
    }

    /**
     * create the exception
     */
    public IDReservedException(String id) {
        super("ID is already reserved: "+id, id);
    }
}
